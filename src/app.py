import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.messagebox
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Paths
ROOT_PATH = Path(__file__).parent.parent

ASSETS_PATH = ROOT_PATH / "assets"
WATERMARK_PATH = ASSETS_PATH / "cropps_watermark_dark.png"
ICO_PATH = ASSETS_PATH / "CROPPS_vertical_logo.png"
BG_PATH = ASSETS_PATH / "cropps_background.png"

DATA_PATH = ROOT_PATH / "src" / "data"
DLL_PATH = ROOT_PATH / "dlls"
from dlls.windows_setup import configure_path

configure_path(str(DLL_PATH))

from src.analysis.image_analysis import start_analysis, stop_analysis
from src.tools.cutter_control import cutter_app
from src.tools.loggernet import Loggernet
from src.tools.sms_sender import SmsSender
from src.tools.trigger import Trigger
from src.ui.camera import Camera
from src.ui.chatbox import Chatbox
from src.ui.histogram import Histogram
from src.ui.loading_screen import LoadingScreen

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 1600, 900
SAVE_FREQ = 3


def threaded(target):
    """Wrapper to run a function in a separate thread with @threaded decorator"""
    return lambda *args, **kwargs: threading.Thread(
        target=target, args=args, kwargs=kwargs, daemon=True
    ).start()


class CameraApp(tk.Tk):
    def __init__(self, argv):
        super().__init__()
        self.title("CROPPS Camera Control")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.state("zoomed")
        self.icon = tk.PhotoImage(file=ICO_PATH)
        self.iconphoto(False, self.icon)
        self._last_msg_history = []
        self._parse_args(argv)

        self._setup_ok_event = threading.Event()
        self.camera = Camera(self._setup_ok_event)
        threading.Thread(target=self.camera.setup).start()
        self.loading_screen = LoadingScreen(self)
        self._setup_ui_after_camera()

    def quit(self):
        print("Exiting...")
        # self.stop_analysis()
        try:
            self.after_cancel(self.update_pid)
            self.camera.image_acquisition_thread.stop()
            self.camera.camera.dispose()
            self.camera.sdk.dispose()
            self.destroy()
            print("Exited successfully")
        finally:
            os.kill(os.getpid(), 2)

    ## main update function ##
    def update_camera_feed(self):
        """Update the camera feed in the GUI window."""
        # === Main camera (self.camera) ===
        # Get latest image from camera
        try:
            pil_image = self.camera.latest_image()
        except IndexError:
            self.after(10, self.update_camera_feed)
            return
        self.imgtk = ImageTk.PhotoImage(image=pil_image)

        # Resize to fit canvas
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        pil_image.thumbnail(
            (canvas_width, canvas_height), Image.Resampling.LANCZOS)

        self.canvas.delete("all")

        x = (canvas_width - pil_image.width) // 2
        y = (canvas_height - pil_image.height) // 2
        self.canvas.create_image(x, y, anchor=tk.NW, image=self.imgtk)

        # Update histogram if frame exists
        if not self.loggernet.stop_event.is_set(): self.loggernet.update(0)
        self.loggernet_canvas.draw_idle()

        # === GRAPHS ===
        if self.show_graph:
            self.histogram.update(pil_image)
            self.histogram_canvas.draw_idle()

        # === OpenCV webcam feed (self.cap) ===
        if hasattr(self, "cap") and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)

                pil_image = self._process_frame(frame, "Live Streaming")

                # Resize to fit a portion of the window
                canvas_width = self.webcam_canvas.winfo_width()
                canvas_height = self.webcam_canvas.winfo_height()
                pil_image = pil_image.copy()
                pil_image.thumbnail((canvas_width, canvas_height),
                                    Image.Resampling.LANCZOS)
                self.imgtk_web = ImageTk.PhotoImage(image=pil_image)
                self.webcam_canvas.delete("all")

                x = (canvas_width - img.width) // 2
                y = (canvas_height - img.height) // 2

                self.webcam_canvas.imgtk = self.imgtk
                self.webcam_canvas.create_image(x, y, anchor=tk.NW,
                                                image=self.imgtk_web)

        self.update_pid = self.after(10, self.update_camera_feed)

    ## main functions for buttons ##
    def start_stop_recording(self):
        """Start recording video."""
        return self.camera.start_stop_recording(self.start_record_button)

    def start_analysis(self):
        assert not self.camera.recording
        self.screenshot_directory = self.start_stop_recording()

        self.capture_task = start_analysis(
            self.camera, self.screenshot_directory, self.start_analysis_button
            if hasattr(self, "start_analysis_button") else None,
            self.stop_analysis)

    def stop_analysis(self):
        if not (self.camera.recording and self.capture_task): return

        if self.capture_task.is_alive():
            self.capture_task.stop()
            self.capture_task.join()

        self.start_stop_recording()

        stop_analysis(self.sms_sender, self.screenshot_directory,
                      self.start_analysis_button
                      if hasattr(self, "start_analysis_button") else None,
                      self.start_analysis)

        self.capture_task = None

    def sms_info(self):
        self.sms_sender.show_dialog(tk.Toplevel(self))

    def show_exposure_dialog(self):
        self.camera.show_exposure_dialog(
            tk.Toplevel(self),
            self.winfo_x(), self.winfo_y(),
            self.winfo_width(), self.winfo_height())

    def save_graph(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        file_name = ROOT_PATH / "saves" / f"graph_{timestamp}.png"
        file_name.parent.mkdir(parents=True, exist_ok=True)
        self.histogram.fig.savefig(file_name)

    def open_pattern_app(self):
        try:
            os.chdir(ROOT_PATH)
            subprocess.Popen(['python', 'cropps-pattern/main.py'])
            print("[INFO] Pattern app started")
        except Exception as e:
            tkinter.messagebox.showerror("Error",
                                         f"Could not open external app: {e}")

    ## setup helpers ##
    def _create_widgets(self):
        """Create all the GUI buttons."""

        def on_frame_configure(_):
            """Reset the scroll region to encompass the inner frame"""
            self.button_canvas.configure(
                scrollregion=self.button_canvas.bbox("all"))

        def on_canvas_configure(event):
            """When canvas is resized, resize the inner frame to match"""
            min_width = self.button_frame.winfo_reqwidth()
            if event.width < min_width:
                # Canvas is smaller than total button width, so expand canvas to fit all content
                self.button_canvas.itemconfig("self.button_frame",
                                              width=min_width)
            else:
                # Canvas is larger than needed, so shrink canvas to fit window
                self.button_canvas.itemconfig("self.button_frame",
                                              width=event.width)

        # Start Recording Button
        self.start_record_button = tk.Button(
            self.button_frame,
            text="Start Recording",
            command=self.start_stop_recording,
            font=("Arial", 16),
        )
        self.start_record_button.pack(side="left", padx=20)

        # Analysis buttons
        self.start_analysis_button = tk.Button(
            self.button_frame,
            text="Start Analysis",
            fg="darkgreen",
            command=self.start_analysis,
            font=("Arial", 16),
        )
        self.start_analysis_button.pack(side="left", padx=20)

        # Set SMS information Button
        self.set_sms_button = tk.Button(
            self.button_frame,
            text="SMS Info",
            command=self.sms_info,
            font=("Arial", 16),
        )
        self.set_sms_button.pack(side="left", padx=20)

        # Set exposure button
        self.exposure_button = tk.Button(self.button_frame,
                                         text="Exposure Settings",
                                         command=self.show_exposure_dialog,
                                         font=("Arial", 16))
        self.exposure_button.pack(side="left", padx=10)

        # Triggers
        self.triggers_button = tk.Button(self.button_frame,
                                         text="Settings...",
                                         command=self._show_trigger_settings,
                                         font=("Arial", 16))
        self.triggers_button.pack(side="left", padx=5)

        # Save graph
        # self.save_graph_button = tk.Button(self.button_frame,
        #                                    text="Save graph",
        #                                    command=self.save_graph)
        # self.save_graph_button.pack(side="left", padx=10)

        self.pattern_button = tk.Button(
            self.button_frame,
            text="Open analyzer",
            command=self.open_pattern_app,
            font=("Arial", 16)
        )
        self.pattern_button.pack(side="left", padx=10)

        # Close Button
        self.quit_button = tk.Button(
            self.button_frame, text="Exit", command=self.quit,
            font=("Arial", 16)
        )
        self.quit_button.pack(side="left", padx=20, pady=5)

        # Bind events to handle canvas resizing
        self.button_frame.bind("<Configure>", on_frame_configure)
        self.button_canvas.bind("<Configure>", on_canvas_configure)

    def _execute_trigger(self, new_msg=None):
        """
        Detects new messages received from the phone, and executes the
        corresponding function.
        """
        if not new_msg:
            # self._show_serial_port_dialog()
            new_msg = self.sms_sender.new_msgs.get()

        print("Message received:", new_msg)

        # Magic number here: analysis timeout
        analysis_timeout = 20

        try:
            self.sms_sender.send_msg_after_message(new_msg, self)
            self.trigger.execute_trigger(new_msg)

            # I just found out python has pattern matching!!!!!
            match new_msg:
                case "current injection" | '1' | "burn" | '2':
                    threading.Thread(
                        target=self.capture_task.start_timer,
                        args=(analysis_timeout, self.stop_analysis),
                        daemon=True).start()
                case "cutter":
                    threading.Thread(target=cutter_app).start()
                case "quit" | 'q':
                    self.send_msg(self.template["received"]["quit"])
                    self.quit()
        except Exception as e:
            tkinter.messagebox.showerror("Error", f"An error occurred while "
                                                  f"attempting to execute trigger: {e}")

    @threaded
    def _init_sms_receiver(self):
        threading.Thread(target=self.sms_sender.read_msg,
                         daemon=True).start()
        print("Message observer started")
        print("[poll_messages]: Process spawned")
        while True:
            self.chatbox.poll_messages(self._execute_trigger,
                                       self.truncate_msgs)

    def _load_watermark(self, watermark_path):
        """Load the watermark image and resize it."""
        if watermark_path.exists():
            self.watermark = Image.open(watermark_path)
            self.watermark = self.watermark.resize((300, 150))
            # Pre-convert to RGBA
            if self.watermark.mode != "RGBA":
                self.watermark = self.watermark.convert("RGBA")
        else:
            self.watermark = Image.new("RGBA", (200, 100))

    def _setup_canvases(self):
        # --- Main frame to hold camera (left) + logger (right) ---
        main_frame = tk.Frame(self)
        main_frame.pack(side="top", fill="both", expand=True)

        width = self.winfo_screenwidth() // 2
        height = self.winfo_screenheight() // 2

        # Keyboard bindings
        def stop(_):
            if self.capture_task: self.stop_analysis()

        self.bind('s', stop)

        self.bind('q', lambda _: self.quit())

        def display_all(_):
            self.truncate_msgs = not self.truncate_msgs
            self.chatbox.refresh_chatbox(self.truncate_msgs)

        self.bind("<space>", display_all)

        if not self.show_buttons:
            self.bind("<Button-1>", lambda _: self.sms_info())

        # --- Left side: Camera feed ---
        camera_frame = tk.Frame(main_frame, width=width, height=height)
        camera_frame.pack(side="left", fill="both", expand=True)
        camera_frame.pack_propagate(False)

        header_frame = tk.Frame(camera_frame)
        header_frame.pack(side="top", fill="x")

        self.canvas = tk.Canvas(camera_frame, width=width, height=height)
        self.canvas.pack(side="top", fill="both", expand=True)

        # --- Right side: Logo + webcam + histogram ---
        right_frame = tk.Frame(main_frame, width=width, height=height)
        right_frame.pack(side="left", fill="both", expand=True)
        right_frame.pack_propagate(False)

        # --- Top: Logo ---
        # UPDATE v2.1.0: putting logo on the left
        try:
            logo_img = self.watermark
            # logo_img = logo_img.resize((200, 100))
            self.logo_photo = ImageTk.PhotoImage(logo_img)

            logo_label = tk.Label(header_frame, image=self.logo_photo)
            # logo_label = tk.Label(right_frame, image=self.logo_photo)

        except Exception as e:
            print(f"Error loading logo: {e}")
            logo_label = tk.Label(
                right_frame,
                text="CROPPS",
                font=("Arial", 24, "bold"),
                fg="#333")
        finally:
            logo_label.pack(side="left", anchor="nw", padx=50, pady=20)
            # logo_label.pack(side="top", anchor="n", pady=(10, 5))

        tk.Label(
            header_frame,
            text="Hi, I’m Ari!",
            font=("Trebuchet MS", 48, "bold"),
            fg="#000000",
            height=logo_label.winfo_height()).pack(side="right", anchor="sw",
                                                   pady=20)

        # --- Placeholder on the right ---
        tk.Label(
            right_frame,
            text="",
            font=("Arial", 24, "bold"),
            fg="#333",
            height=logo_label.winfo_height()
        ).pack(side="top", anchor="nw", padx=50, pady=20)

        # --- Middle: Webcam canvas ---
        if self.show_webcam:
            webcam_height = (
                self.winfo_screenheight() / 2.5
                if self.show_graph
                else height - 120
            )
            self.webcam_canvas = tk.Canvas(
                right_frame, width=width, height=webcam_height)
            self.webcam_canvas.pack(side="top", fill="both", expand=True,
                                    pady=(5, 10))

        if self.show_graph:
            hist_frame = tk.Frame(right_frame)
            hist_frame.pack(side="bottom", fill="x", pady=(0, 10))
            self.histogram_canvas = FigureCanvasTkAgg(self.histogram.fig,
                                                      master=hist_frame)
            self.histogram_canvas.get_tk_widget().pack(fill="x", expand=True)

            # --- Bottom: Histogram ---
            self.loggernet_frame = tk.Frame(right_frame)
            self.loggernet_frame.pack(side="bottom", fill="x", pady=(0, 10))
            self.loggernet_canvas = FigureCanvasTkAgg(self.loggernet.fig,
                                                      master=self.loggernet_frame)
            self.loggernet_canvas.get_tk_widget().pack(fill="x", expand=True)

        # --- Chatbox ---
        chat_frame = tk.Frame(right_frame, bg="white")
        chat_frame.pack(side="top", fill="both", expand=True, padx=10,
                        pady=(175, 0))  # add vspace above the phone screen

        if self.show_graph:
            # Regular chat box
            chat_label = tk.Label(chat_frame, text="Message History",
                                  font=("Arial", 14, "bold"), bg="white")
            chat_label.pack(anchor="n")

            # ScrolledText for chat messages
            # font size for chatbox (magic number)
            self.chatbox = Chatbox(chat_frame, self.sms_sender, self["bg"])
            self.chatbox.pack(fill="both", expand=True, pady=(5, 0))
        else:
            # Image of a screen
            canvas = tk.Canvas(chat_frame)
            canvas.pack(fill="both", expand=True)
            try:
                # height of screen (magic number)
                height = int(self.winfo_height() * .7)

                img = Image.open("assets/screen.png")
                img = img.resize((int(height * img.width / img.height), height))
                imgtk = ImageTk.PhotoImage(img)
                canvas.img = imgtk  # ugh garbage collection...
                canvas.create_image(self.winfo_width() // 4, 0, anchor="n",
                                    image=imgtk)

                # ScrolledText for chat messages
                self.chatbox = Chatbox(chat_frame, self.sms_sender, self["bg"])

                # dimensions of chatbox (magic numbers)
                chatbox_width = imgtk.width() * .4
                chatbox_height = imgtk.height() * .7

                canvas.create_window(self.winfo_width() // 4,
                                     imgtk.height() // 2, anchor="center",
                                     window=self.chatbox, width=chatbox_width,
                                     height=chatbox_height)
            except Exception as e:
                print(f"Error loading assets: {e}")

    def _setup_scroll_frame(self):
        """Setup scroll frame for buttons"""
        scroll_frame = tk.Frame(self)
        scroll_frame.pack(side="bottom", fill="x", pady=10)

        h_scrollbar = tk.Scrollbar(scroll_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")

        self.button_canvas = tk.Canvas(
            scroll_frame, height=60, xscrollcommand=h_scrollbar.set
        )
        self.button_canvas.pack(side="bottom", fill="x", pady=5)

        self.button_frame = tk.Frame(self.button_canvas)
        self.button_canvas.create_window(
            (0, 0), window=self.button_frame, anchor="nw",
            tags="self.button_frame"
        )
        h_scrollbar.config(command=self.button_canvas.xview)

    def _setup_ui_after_camera(self):
        """Setup UI after camera initialization"""
        # Remove loading screen
        if self.camera.setup_failed_event.is_set():
            tkinter.messagebox.showerror("Error loading camera",
                                         self.camera.err)
            self.quit()

        if not self._setup_ok_event.is_set():
            self.after(50, self._setup_ui_after_camera)
            return

        self.loading_screen.__del__()

        # Continue with regular UI setup
        self.video_writer = None
        self.analyzing = False
        self.capture_task = None
        self.imgtk = None
        self.current_injection_port_com = 3
        self.burn_port_com = 4
        self.current_injection_port_com = 3
        self.burn_port_com = 4

        self.histogram = Histogram()
        self.sms_sender = SmsSender()
        self.trigger = Trigger(pre_trigger_func=self.start_analysis)

        if self.show_graph:
            self.loggernet = Loggernet()

        if self.show_webcam:
            self.cap = cv2.VideoCapture(0)

        # Setup UI components
        self._load_watermark(WATERMARK_PATH)
        self._setup_canvases()

        # UPDATE v2.1.0: most button is hidden if `self.hide_buttons`
        if self.show_buttons:
            self._setup_scroll_frame()
            self._create_widgets()

        # Start camera feed
        self._init_sms_receiver()
        self.update_camera_feed()

    def _show_trigger_settings(self):
        self.trigger.show_settings(tk.Toplevel(self), self._execute_trigger,
                                   self.winfo_x(), self.winfo_y(),
                                   self.winfo_width(), self.winfo_height())

    def _parse_args(self, argv):
        # Using argv here:
        # Toggle graphs and webcam feed
        self.show_buttons = self.show_graph = self.truncate_msgs = self.show_webcam = False
        for arg in argv[1:]:
            if arg.startswith('-'):
                if 'b' in arg:
                    self.show_buttons = True
                if 'g' in arg:
                    self.show_graph = True
                if 't' in arg:
                    self.truncate_msgs = True
                if 'w' in arg:
                    self.show_webcam = True
            elif arg.startswith("--"):
                match arg:
                    case "--show-buttons":
                        self.show_buttons = True
                    case "--show-graphs":
                        self.show_graph = True
                    case "--truncate-messages":
                        self.truncate_msgs = True
                    case "--show-webcam":
                        self.show_webcam = True
                    case _:
                        print("Unknown argument: ", arg)
                        os.kill(os.getpid(), 2)
            else:
                print("Unknown argument: ", arg)
                print(f"Hint: did you mean -{arg}?")
                os.kill(os.getpid(), 2)

    def _process_frame(self, frame, text):
        """ Add text to frame """
        # """Overlay the watermark on the frame."""
        # Convert the frame to RGB (from BGR)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert frame to a PIL image
        pil_image = Image.fromarray(frame_rgb)

        # Add text
        font = ImageFont.truetype("arial.ttf", size=40)
        ImageDraw.Draw(pil_image).text((50, 50), text, font=font,
                                       fill=(255, 255, 255))

        # # Overlay watermark at bottom right corner (can change position)
        # watermark_width, watermark_height = self.watermark.size
        # padding = 10
        # pil_image.paste(
        #     self.watermark,
        #     (
        #         0 + padding,
        #         0 + padding,
        #     ),
        #     self.watermark,
        # )
        return pil_image


def main(argv):
    app = CameraApp(argv)
    app.mainloop()
