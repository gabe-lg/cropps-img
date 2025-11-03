import os
import sys
import threading
import time
import tkinter as tk
import tkinter.messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path

import cv2
from instrumental import Q_

# Ensure project root is on sys.path when running this file directly
if __name__ == "__main__" or __package__ is None:
    _project_root = str(Path(__file__).resolve().parents[1])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

# import src.cutter_control
import src.analyzer
import src.loggernet
from src.trigger import Trigger
from src.image_analysis import image_analysis
from src.remote_image_analysis import remote_image_analysis

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageDraw, ImageFont, ImageTk
from src.capture_task import CaptureTask
from src.camera import Camera

# Paths
WATERMARK_PATH = Path(__file__).parent.parent / "assets" / "cropps_watermark_dark.png"
ICO_PATH = "./assets/CROPPS_vertical_logo.png"
BG_PATH = Path(__file__).parent.parent / "assets" / "cropps_background.png"

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 1600, 900
DEVICE_INDEX = 0
QUERY_TIME = 0.05  # Buffer time for Dino-Lite to return value
COMMAND_TIME = 0.25  # Buffer time to allow Dino-Lite to process command


def threaded(target):
    """Wrapper to run a function in a separate thread with @threaded decorator"""
    return lambda *args, **kwargs: threading.Thread(
        target=target, args=args, kwargs=kwargs, daemon=True
    ).start()


class CameraApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CROPPS Camera Control")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.state("zoomed")
        self.icon = tk.PhotoImage(file=ICO_PATH)
        self.iconphoto(False, self.icon)
        # TODO: add button that toggles whether data is displayed in camera feed
        self.show_logger = True
        self.threads = []

        # self.resizable(False, False)
        # self.attributes('-fullscreen', True)

        # Show loading screen in main window
        self.loading_frame = tk.Frame(self)
        self.loading_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Load and display background
        try:
            bg_image = Image.open(BG_PATH)
            bg_image = bg_image.resize((400, 300))
            self.bg_photo = ImageTk.PhotoImage(bg_image)
            bg_label = tk.Label(self.loading_frame, image=self.bg_photo)
            bg_label.pack()
        except Exception as e:
            print(f"Error loading background: {e}")
            self.loading_frame.configure(bg="white")

        # Create canvas for rotating circle
        self.loading_canvas = tk.Canvas(self.loading_frame, width=50, height=50)
        self.loading_canvas.pack(pady=(20, 5))  # Reduced bottom padding

        # Add loading text
        self.loading_text = tk.Label(
            self.loading_frame, text="Loading...", font=("Comic Sans MS", 16)
        )
        self.loading_text.pack(pady=(0, 20))

        # Initialize loading animation
        self.angle = 60
        self._animate_loading()
        self.current_injection_port = "COM3"
        self.burn_port = "COM4"

        self.show_graph = False
        # self.show_graph = tk.messagebox.askyesno("Graphs", "Show graphs?")

        self.trigger = Trigger(pre_trigger_func=self.start_analysis)

        # Initialize camera in separate thread
        try:
            self.camera = Camera()
        except Exception as e:
            self.camera = None
            print(f"Error loading camera: {e}")

        # Initialize camera/UI setup on the main thread
        self._init_camera_thread()
        self._last_msg_history = []
        self.after(2000, self._poll_messages)

    def quit(self):
        # self.sms_sender.send_debug_msg("Exiting...")
        # self.stop_analysis()
        for t in self.threads:
            try: t.join()
            except: continue
        self.camera = None
        self.destroy()

    ## main update function ##
    def update_camera_feed(self):
        """Update the camera feed in the GUI window."""
        # === Main camera (self.camera) ===
        if hasattr(self, "camera"):
            if self.camera:
                frame = self.camera.get_frame()
                if frame is not None:
                    # if hasattr(self, 'capture_task') and self.capture_task is not None:
                    # self.capture_task.set_frame(frame)
                    # self.analyzer.paint_square(frame)
                    if self.camera.is_recording():
                        self.camera.write_video_frame()

                    pil_image = self._process_frame(frame)

                    # Resize to fit canvas
                    canvas_width = self.canvas.winfo_width()
                    canvas_height = self.canvas.winfo_height()
                    pil_image = pil_image.copy()
                    pil_image.thumbnail(
                        (canvas_width, canvas_height), Image.Resampling.LANCZOS
                    )
                    self.imgtk = ImageTk.PhotoImage(image=pil_image)
                    self.canvas.delete("all")

                    x = (canvas_width - pil_image.width) // 2
                    y = (canvas_height - pil_image.height) // 2
                    self.canvas.create_image(x, y, anchor=tk.NW, image=self.imgtk)

                    # Update histogram if frame exists
                    # if not self.loggernet.stop_event.is_set(): self.loggernet.update(
                    #     0)
                    # self.loggernet_canvas.draw_idle()

                else:
                    self.canvas.delete("all")
                    self.imgtk = None

            if self.show_graph:
                self.histogram.update(frame)
                self.canvas.create_rectangle(0, 0, self.canvas.winfo_width(),
                                             self.canvas.winfo_height(),
                                             fill="black", outline="")
                self.histogram_canvas.draw_idle()

        # === OpenCV webcam feed (self.cap) ===
        if hasattr(self, "cap") and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)

                # Resize to fit a portion of the window
                canvas_width = self.webcam_canvas.winfo_width()
                canvas_height = self.webcam_canvas.winfo_height()
                img = img.copy()
                img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                imgtk = ImageTk.PhotoImage(image=img)
                self.webcam_canvas.delete("all")

                x = (canvas_width - img.width) // 2
                y = (canvas_height - img.height) // 2

                self.webcam_canvas.imgtk = imgtk
                self.webcam_canvas.create_image(x, y, anchor=tk.NW, image=imgtk)

        # Repeat this method after a short delay
        self.after(1000 // self.camera.app_fps, self.update_camera_feed)

    ## main functions for buttons ##
    @threaded
    def capture(self):
        """Capture an image when the button is pressed."""
        frame = self.camera.get_frame()
        if frame is not None:
            self.capture_task.capture_image(frame)
            tkinter.messagebox.showinfo("Capture", "Image captured successfully.")
        else:
            tkinter.messagebox.showerror("Capture", "Failed to capture image.")

    def start_recording(self):
        """Start recording video."""
        file_name = self.camera.start_recording()
        self.start_record_button.config(state="disabled")
        tkinter.messagebox.showinfo(
            "Recording", f"Video recording started. File: {file_name}"
        )

    def stop_recording(self):
        """Stop recording video."""
        if self.camera.is_recording():
            self.camera.stop_recording()
            self.start_record_button.config(state="normal")
            tkinter.messagebox.showinfo("Recording", "Video recording stopped.")
        else:
            tkinter.messagebox.showinfo("Recording", "No video is currently recording.")

    def start_analysis(self, prefix=None):
        project_root = Path(__file__).resolve().parent.parent
        assets_dir = project_root / "assets" / "captured_data"

        self.screenshot_directory = (
            assets_dir / f"analysis_{time.strftime('%Y%m%d_%H%M%S')}"
        )
        self.screenshot_directory.mkdir(parents=True, exist_ok=True)
        self.capture_task = CaptureTask(self.camera, self.screenshot_directory)
        self.capture_task.start()
        self.start_analysis_button.config(
            text="Stop Analysis", fg="darkred", command=self.stop_analysis
        )

    def stop_analysis(self):
        if self.capture_task.is_alive():
            self.capture_task.stop()
            self.capture_task.join()
        self.start_analysis_button.config(
            text="Start Analysis", fg="darkgreen", command=self.start_analysis
        )

        # variable to control remote/local analysis
        REMOTE = False

        # Show a non-blocking "waiting" message
        waiting_win = tk.Toplevel()
        waiting_win.title("Please wait")
        tk.Label(
            waiting_win,
            text=f"Running {"remote" if REMOTE else "local"} analysis...\nThis may take a while.",
        ).pack(padx=30, pady=30)

        @threaded
        def worker():
            try:
                if REMOTE:
                    result = remote_image_analysis(self.screenshot_directory)
                else:
                    result = image_analysis(self.screenshot_directory)
                self.after(
                    0,
                    lambda: tkinter.messagebox.showinfo(
                        "Analysis Result", f"Detection result: {result}"
                    ),
                )

                if self.sms_sender.phone:
                    text_body = None
                    match result.lower().strip():
                        case "current injection":
                            self.sms_sender.send_msg(
                                self.sms_sender.phone,
                                "You gave me a tickle with that current—jolt confirmed! ⚡",
                            )
                        case "burn":
                            self.sms_sender.send_msg(
                                self.sms_sender.phone,
                                "Ouch! You hit me with a burn—fireworks on my leaves! 🔥",
                            )
                        case _:
                            self.sms_sender.send_msg(
                                self.sms_sender.phone,
                                "All quiet here — no tickles or burns. I’m just chilling. 🌿",
                            )

            except Exception as e:
                self.after(
                    0,
                    lambda: tkinter.messagebox.showerror(
                        "Analysis Error", f"Failed to analyze images: {e}"
                    ),
                )
            finally:
                self.after(0, waiting_win.destroy)

        worker()
        self.capture_task = None

    def sms_info(self):
        sms_dialog = tk.Toplevel(self)
        sms_dialog.title("Enter SMS Details")
        sms_dialog.config(bg="white")

        # create label and checkbox for receiving messages
        receive_sms_var = tk.BooleanVar()
        receive_sms_label = tk.Label(
            sms_dialog,
            text="Would you like to receive text messages from a plant?",
            font=("TkTextFont", 18),
            bg="white",
        )
        receive_sms_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        receive_sms_checkbox = tk.Checkbutton(
            sms_dialog, variable=receive_sms_var, bg="white"
        )
        receive_sms_checkbox.grid(row=0, column=2, padx=10, pady=10)

        # create label and input for the name
        name_label = tk.Label(
            sms_dialog, text="Enter name: ", font=("TkTextFont", 18), bg="white"
        )
        name_label.grid(row=1, column=0, padx=10, pady=10)
        name_entry = tk.Entry(sms_dialog)
        name_entry.grid(row=1, column=1, padx=10, pady=10)

        # create label and input for the phone number
        contact_label = tk.Label(
            sms_dialog, text="Enter phone number: ", font=("TkTextFont", 18), bg="white"
        )
        contact_label.grid(row=2, column=0, padx=10, pady=10)
        contact_entry = tk.Entry(sms_dialog)
        contact_entry.grid(row=2, column=1, padx=10, pady=10)

        # Label for displaying error messages
        error_label = tk.Label(
            sms_dialog, text="", fg="red", font=("TkTextFont", 18), bg="white"
        )
        error_label.grid(row=3, column=0, columnspan=2, padx=12, pady=10)

        def send_info():
            name = name_entry.get()
            contact = contact_entry.get()

            # Only set contact info if the checkbox is checked
            if receive_sms_var.get():
                if not name or not contact:
                    error_label.config(text="Please provide a name and phone number.")
                else:
                    self.sms_sender.set_info(name, contact)
                    self.sms_sender.send_msg(
                        contact,
                        f"Hi {name}, it’s me, your plant Arabella the Arabidopsis. These scientists have wired me up like a bio-battery on my leaves, sending currents that range from a gentle tickle to a fiery burn that leaves me smoking. Help a plant out: send sunlight, water, or a hilarious meme to recharge my spirits. Don’t leaf me in the dark! 🌿⚡🔥",
                    )
                    self.sms_sender.send_msg(
                        contact,
                        f"Psst, {name}... feeling adventurous? You can control my fate from afar! Reply '1' for a tickle or '2' for a burn—like a dramatic fireworks show on my leaves. Which thrill will you pick? Reply now! ⚡1 or 🔥2?",
                    )
                    sms_dialog.destroy()
            else:
                error_label.config(text="Please check the box and provide all details.")

        # Create Save button
        save_button = tk.Button(sms_dialog, text="Save", command=send_info)
        save_button.grid(row=4, column=0, padx=10, pady=10)

        # Create Cancel button
        cancel_button = tk.Button(sms_dialog, text="Cancel", command=sms_dialog.destroy)
        cancel_button.grid(row=4, column=1, padx=10, pady=10)

        image = tk.PhotoImage(file=BG_PATH)  # Change to the correct path to your image
        image_label = tk.Label(sms_dialog, image=image)
        image_label.grid(
            row=5, column=0, columnspan=2, padx=2, pady=10
        )  # Place the image under the buttons
        image_label.image = image  # Keep a reference to the image to prevent it from being garbage collected

        sms_dialog.mainloop()

    def show_exposure_dialog(self):
        def apply():
            exposure_value = Q_(float(exposure_entry.get()), "millisecond")
            self.camera.set_exposure(exposure_value)
            dialog.destroy()
            (
                tkinter.messagebox.showinfo(
                    "Exposure", f"Exposure set to {self.camera.get_exposure()}s"
                )
            )

        dialog = tk.Toplevel(self)
        dialog.title("Exposure Settings")
        dialog.geometry("400x150")
        dialog.resizable(False, False)

        content_frame = tk.Frame(dialog)
        content_frame.pack(expand=True, fill="both", padx=20, pady=20)

        current_label = tk.Label(
            content_frame, text=f"Current Exposure: {self.camera.get_exposure():,}s"
        )
        current_label.pack(pady=(0, 10))

        input_frame = tk.Frame(content_frame)
        input_frame.pack(fill="x", pady=5)

        tk.Label(input_frame, text="New exposure:").pack(side="left")
        exposure_entry = tk.Entry(input_frame, width=25)
        exposure_entry.pack(side="left", padx=10)
        tk.Label(input_frame, text="milliseconds").pack(side="left", padx=2)

        button_frame = tk.Frame(content_frame)
        button_frame.pack()

        tk.Button(button_frame, text="Apply", command=apply, width=10).pack(
            side="left", padx=5
        )
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(
            side="left", padx=5
        )

        exposure_entry.bind("<Return>", lambda e: apply())

        # Center the dialog on the main window
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def show_fps_dialog(self):
        def apply():
            fps_value = fps_entry.get()
            self.camera.set_fps(fps_value)
            dialog.destroy()
            (
                tkinter.messagebox.showinfo(
                    "Framerate", f"Framerate set to {self.camera.get_fps():,}"
                )
            )

            # error_label.config(
            #     text=f"Please enter a valid value between {mn} and {mx}.")

        dialog = tk.Toplevel(self)
        dialog.title("Framerate Settings")
        dialog.geometry("400x150")
        dialog.resizable(False, False)

        content_frame = tk.Frame(dialog)
        content_frame.pack(expand=True, fill="both", padx=20, pady=20)

        current_label = tk.Label(
            content_frame, text=f"Current Framerate: {self.camera.get_fps():,}"
        )
        current_label.pack(pady=(0, 10))

        input_frame = tk.Frame(content_frame)
        input_frame.pack(fill="x", pady=5)

        tk.Label(input_frame, text="New framerate:").pack(side="left")
        fps_entry = tk.Entry(input_frame, width=25)
        fps_entry.pack(side="left", padx=10)
        tk.Label(input_frame, text="Hertz").pack(side="left", padx=2)

        button_frame = tk.Frame(content_frame)
        button_frame.pack()

        tk.Button(button_frame, text="Apply", command=apply, width=10).pack(
            side="left", padx=5
        )
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(
            side="left", padx=5
        )

        fps_entry.bind("<Return>", lambda e: apply())

        # Center the dialog on the main window
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def save_graph(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        file_name = Path(__file__).parent.parent / "saves" / f"graph_{timestamp}.png"
        file_name.parent.mkdir(parents=True, exist_ok=True)
        self.histogram.fig.savefig(file_name)

    ## setup helpers ##
    def _animate_loading(self):
        """Animate the loading circle"""
        if hasattr(self, "camera"):
            return

        self.loading_canvas.delete("all")

        # Draw rotating arc
        # TODO: Bad loading icon
        self.loading_canvas.create_arc(
            5, 5, 45, 45, start=self.angle, extent=300, fill="", outline="blue", width=2
        )

        self.angle = (self.angle - 10) % 360
        self.after(50, self._animate_loading)

    def _create_widgets(self):
        """Create all the GUI buttons."""

        def on_frame_configure(_):
            """Reset the scroll region to encompass the inner frame"""
            self.button_canvas.configure(scrollregion=self.button_canvas.bbox("all"))

        def on_canvas_configure(event):
            """When canvas is resized, resize the inner frame to match"""
            min_width = self.button_frame.winfo_reqwidth()
            if event.width < min_width:
                # Canvas is smaller than total button width, so expand canvas to fit all content
                self.button_canvas.itemconfig("self.button_frame", width=min_width)
            else:
                # Canvas is larger than needed, so shrink canvas to fit window
                self.button_canvas.itemconfig("self.button_frame", width=event.width)

        # # Capture Button
        # self.capture_button = tk.Button(self.button_frame, text="Capture Image",
        #                                 command=self.capture,font=("Arial", 16))
        # self.capture_button.pack(side="left", padx=20)

        # TODO: Hide buttons if camera not detected

        # Start Recording Button
        self.start_record_button = tk.Button(
            self.button_frame,
            text="Start Recording",
            command=self.start_recording,
            font=("Arial", 16),
        )
        self.start_record_button.pack(side="left", padx=20)

        # Stop Recording Button
        self.stop_record_button = tk.Button(
            self.button_frame,
            text="Stop Recording",
            command=self.stop_recording,
            font=("Arial", 16),
        )
        self.stop_record_button.pack(side="left", padx=20)

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

        # Triggers
        self.triggers_button = tk.Menubutton(
            self.button_frame, text="Triggers...", font=("Arial", 16)
        )
        self.triggers_menu = tk.Menu(self.triggers_button, tearoff=0)
        self.triggers_button.config(menu=self.triggers_menu)

        self.triggers_menu.add_command(
            label="Current Injection",
            command=lambda: self.trigger.injection(self.current_injection_port),
            font=("Arial", 16),
        )
        self.triggers_menu.add_command(
            label="Burn",
            command=lambda: self.trigger.burn(self.burn_port),
            font=("Arial", 16),
        )

        self.triggers_button.pack(side="left", padx=5)

        # Save graph
        # self.save_graph_button = tk.Button(self.button_frame,
        #                                    text="Save graph",
        #                                    command=self.save_graph)
        # self.save_graph_button.pack(side="left", padx=10)

        # Close Button
        self.quit_button = tk.Button(
            self.button_frame, text="Exit", command=self.quit, font=("Arial", 16)
        )
        self.quit_button.pack(side="left", padx=20, pady=5)

        # Bind events to handle canvas resizing
        self.button_frame.bind("<Configure>", on_frame_configure)
        self.button_canvas.bind("<Configure>", on_canvas_configure)

    @threaded
    def _init_camera_thread(self):
        """Initialize camera in a separate thread"""
        self.after(0, self._setup_ui_after_camera)

    @threaded
    def _init_sms_receiver(self):
        self.threads.append \
            (threading.Thread(target=self.sms_sender.read_msg).start())
        print("Message observer started")
        self._msg_observer()

    def _load_watermark(self, watermark_path):
        """Load the watermark image and resize it."""

        def get_path(path):
            if path.exists():
                self.watermark = Image.open(watermark_path)
                self.watermark = self.watermark.resize((300, 150))
                # Pre-convert to RGBA
                if self.watermark.mode != "RGBA":
                    self.watermark = self.watermark.convert("RGBA")
            else:
                self.watermark = Image.new("RGBA", (200, 100))

        get_path(watermark_path)

    @threaded
    def _msg_observer(self):
        """
        Detects new messages received from the phone, and executes the
        corresponding function.
        """
        # self._show_serial_port_dialog()
        while True:
            self.sms_sender.new_msg_event.wait()
            new_msg = self.sms_sender.new_msgs.get()
            print("Message received:", new_msg)

            try:
                # I just found out python has pattern matching!!!!!
                match new_msg:
                    case "current injection" | "1":
                        self.trigger.injection(self.current_injection_port)
                    # case "1":
                    #     self.trigger.injection(self.current_injection_port)
                    case "burn" | "2":
                        self.trigger.burn(self.burn_port)
                    # case "2":
                    #     self.trigger.burn(self.burn_port)
                    case "stop":
                        self.stop_analysis()
                    case _:
                        raise ValueError("Not supported")
            except Exception as e:
                print("An error occurred while running external script:", e)
            finally:
                self.sms_sender.new_msg_event.clear()

    @threaded
    def _poll_messages(self):
        """Periodically refresh chatbox with updated message history."""
        try:
            if self.sms_sender and self.sms_sender.phone:
                msgs = self.sms_sender.get_msg_history(self.sms_sender.phone)
                # Only update if there’s new content
                if msgs != getattr(self, "_last_msg_history", []):  
                    self._last_msg_history = msgs
                    self._refresh_chatbox(msgs)

        except Exception as e:
            print("Error polling messages:", e)

        # Schedule again in 3.5 seconds
        self.after(3500, self._poll_messages)

    def _refresh_chatbox(self, msgs):
        """Replace chatbox content with current message history."""
        self.chatbox.configure(state="normal")
        self.chatbox.delete("1.0", "end")

        for m in msgs:
            sender = "You" if m["type"] == "sent" else self.sms_sender.name or "Contact"
            ts = time.strftime("%H:%M:%S", time.localtime(m["timestamp"] / 1000))
            self.chatbox.insert("end", f"[{ts}] {sender}: {m['body']}\n")

        self.chatbox.configure(state="disabled")
        self.chatbox.yview("end")

    def _setup_canvases(self):
        # --- Main frame to hold camera (left) + logger (right) ---
        main_frame = tk.Frame(self)
        main_frame.pack(side="top", fill="both", expand=True)

        # Dynamic sizing based on screen
        width = self.winfo_screenwidth() // 2
        height = self.winfo_screenheight() // 1.5  # adjust if needed

        # --- Left side: Camera feed ---
        camera_frame = tk.Frame(main_frame, width=width, height=height)
        camera_frame.pack(side="left", fill="both", expand=True)
        camera_frame.pack_propagate(False)

        self.canvas = tk.Canvas(camera_frame, width=width, height=height)
        self.canvas.pack(fill="both", expand=True)

        # --- Right side: Logo + webcam + histogram ---
        if self.show_logger:
            right_frame = tk.Frame(main_frame, width=width, height=height)
            right_frame.pack(side="left", fill="both", expand=True)
            right_frame.pack_propagate(False)

            # --- Top: Logo ---
            try:
                logo_img = self.watermark
                # logo_img = logo_img.resize((200, 100))  # adjust as needed
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(right_frame, image=self.logo_photo)
                logo_label.pack(side="top", anchor="n", pady=(10, 5))
            except Exception as e:
                print(f"Error loading logo: {e}")
                logo_label = tk.Label(
                    right_frame,
                    text="CROPPS",
                    font=("Arial", 24, "bold"),
                    fg="#333"
                )
                logo_label.pack(side="top", anchor="n", pady=(10, 5))

            # --- Middle: Webcam canvas ---
            webcam_height = (
                self.winfo_screenheight() / 2.5
                if self.show_graph
                else height - 120  # adjust if logo present
            )
            self.webcam_canvas = tk.Canvas(
                right_frame, width=width, height=webcam_height)
            self.webcam_canvas.pack(side="top", fill="both", expand=True, pady=(5, 10))

            # --- Bottom: Histogram ---
            # --- Chatbox ---
            chat_frame = tk.Frame(right_frame, bg="white", height=200)
            chat_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

            chat_label = tk.Label(chat_frame, text="Message History", font=("Arial", 14, "bold"), bg="white")
            chat_label.pack(anchor="w")

            # ScrolledText for chat messages
            self.chatbox = ScrolledText(chat_frame, wrap="word", height=15, state="disabled", font=("Segoe UI Emoji", 12))
            self.chatbox.pack(fill="both", expand=True, pady=(5, 0))
            # if self.show_graph:
            #     hist_frame = tk.Frame(right_frame)
            #     hist_frame.pack(side="bottom", fill="x", pady=(0, 10))
            #     self.histogram_canvas = FigureCanvasTkAgg(self.histogram.fig, master=hist_frame)
            #     self.histogram_canvas.get_tk_widget().pack(fill="x", expand=True)

        self.imgtk = None  # Keep a reference

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
            (0, 0), window=self.button_frame, anchor="nw", tags="self.button_frame"
        )
        h_scrollbar.config(command=self.button_canvas.xview)

    def _setup_ui_after_camera(self):
        """Setup UI after camera initialization"""
        # Remove loading screen
        self.loading_frame.destroy()

        # Continue with regular UI setup
        self.recording = False
        self.video_writer = None
        self.analyzing = False
        self.capture_task = None
        self.cap = cv2.VideoCapture(0)
        self.histogram = src.analyzer.Histogram()
        self.sms_sender = src.sms_sender.SmsSender()
        if self.show_graph:
            self.loggernet = src.loggernet.Loggernet()

        # Setup UI components
        self._load_watermark(WATERMARK_PATH)
        self._setup_scroll_frame()
        self._setup_canvases()
        self._create_widgets()
        self.imgtk = None

        # Start camera feed
        self._init_sms_receiver()
        self.update_camera_feed()

    # def _show_serial_port_dialog(self):
    #     def apply():
    #         try:
    #             self.current_injection_port = "COM" + str(
    #                 int(current_entry.get().strip())
    #             )
    #             self.burn_port = "COM" + str(int(burn_entry.get().strip()))

    #             dialog.destroy()
    #             print(
    #                 f"Current Injection Port: {self.current_injection_port}\n"
    #                 f"Burn Port: {self.burn_port}"
    #             )
    #         except ValueError:
    #             error_label.config(text="Invalid Serial Port")

    #     dialog = tk.Toplevel(self)
    #     dialog.title("Set Serial Ports")
    #     dialog.geometry("400x200")
    #     dialog.resizable(False, False)

    #     content_frame = tk.Frame(dialog)
    #     content_frame.pack(expand=True, fill="both", padx=20, pady=20)

    #     # ---- Current Injection Port Input ----
    #     current_frame = tk.Frame(content_frame)
    #     current_entry = tk.Entry(current_frame, width=25)
    #     current_entry.pack(side="right", padx=2)
    #     current_frame.pack(fill="x", pady=5)
    #     tk.Label(current_frame, text="Current Injection Port: COM").pack(side="right")

    #     # ---- Burn Port Input ----
    #     burn_frame = tk.Frame(content_frame)
    #     burn_entry = tk.Entry(burn_frame, width=25)
    #     burn_entry.pack(side="right", padx=2)
    #     burn_frame.pack(fill="x", pady=5)
    #     tk.Label(burn_frame, text="Burn Port: COM").pack(side="right")

    #     # ---- Error Label ----
    #     error_label = tk.Label(content_frame, text="", fg="red")
    #     error_label.pack()

    #     # ---- Buttons ----
    #     button_frame = tk.Frame(content_frame)
    #     button_frame.pack(pady=10)
    #     tk.Button(button_frame, text="Apply", command=apply, width=10).pack(
    #         side="left", padx=5
    #     )
    #     tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(
    #         side="left", padx=5
    #     )

    #     # ---- Bind Enter Key ----
    #     current_entry.bind("<Return>", lambda e: apply())
    #     burn_entry.bind("<Return>", lambda e: apply())

    #     # ---- Center the dialog ----
    #     dialog.update_idletasks()
    #     x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
    #     y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
    #     dialog.geometry(f"+{x}+{y}")

    def _process_frame(self, frame):
        """Overlay the watermark on the frame."""
        # Convert the frame to RGB (from BGR)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert frame to a PIL image
        pil_image = Image.fromarray(frame_rgb)

        # Overlay watermark at bottom right corner (can change position)
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


def main():
    app = CameraApp()
    # threading.Thread(target=src.cutter_control.cutter_app).start()
    app.mainloop()
