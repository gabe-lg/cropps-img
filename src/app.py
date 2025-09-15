import cv2
import threading
import time
import tkinter as tk
import tkinter.simpledialog, tkinter.messagebox
import sys
from pathlib import Path

# Ensure project root is on sys.path when running this file directly
if __name__ == "__main__" or __package__ is None:
    _project_root = str(Path(__file__).resolve().parents[1])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

import src.analyzer
import src.cutter_control
import src.loggernet
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageDraw, ImageFont, ImageTk
from src.capture_task import capture_image, CaptureTask
from src.driver_dnx64 import DNX64
from src.camera import Camera

# Paths
WATERMARK_PATH = Path(
    __file__).parent.parent / "assets" / "cropps_watermark.png"
ICO_PATH = "./assets/CROPPS_vertical_logo.png"
BG_PATH = Path(__file__).parent.parent / "assets" / "cropps_background.png"
DNX64_PATH = 'C:\\Users\\CROPPS-in-Box\\Documents\\cropps main folder\\DNX64\\DNX64.dll'

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 1600, 900
CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS = 1280, 960, 30
DEVICE_INDEX = 0
QUERY_TIME = 0.05  # Buffer time for Dino-Lite to return value
COMMAND_TIME = 0.25  # Buffer time to allow Dino-Lite to process command


def threaded(target):
    """Wrapper to run a function in a separate thread with @threaded decorator"""
    return lambda *args, **kwargs: threading.Thread(target=target, args=args,
                                                    kwargs=kwargs).start()


class CameraApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CROPPS Camera Control")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.icon = tk.PhotoImage(file=ICO_PATH)
        self.iconphoto(False, self.icon)
        # TODO: add button that toggles whether data is displayed in camera feed
        self.show_data = True

        # TODO: reduce latency. For now, at least disallow window resizing
        #  since it crashes the app
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
            self.loading_frame.configure(bg='white')

        # Create canvas for rotating circle
        self.loading_canvas = tk.Canvas(self.loading_frame, width=50, height=50)
        self.loading_canvas.pack(pady=(20, 5))  # Reduced bottom padding

        # Add loading text
        self.loading_text = tk.Label(self.loading_frame, text="Loading...",
                                     font=('Comic Sans MS', 16))
        self.loading_text.pack(pady=(0, 20))

        # Initialize loading animation
        self.angle = 60
        self._animate_loading()

        # Initialize camera in separate thread
        self._get_microscope(DNX64_PATH)
        self.camera = Camera()
    # Initialize camera/UI setup on the main thread
    self._init_camera_thread()

    def quit(self):
        self.sms_sender.send_debug_msg("Exiting...")
        self.stop_analysis()
        self.camera.release()
        self.destroy()
        super().quit()

    ## main update function ##
    def update_camera_feed(self):
        """Update the camera feed in the GUI window."""
        if not (hasattr(self, 'camera') and self.camera):
            return

        frame = self.camera.get_frame()
        if frame is not None:
            # Only set frame if capture_task is initialized
            if hasattr(self, 'capture_task') and self.capture_task is not None:
                self.capture_task.set_frame(frame)
            # self.analyzer.paint_square(frame)

            pil_image = self._overlay_watermark(frame)
            pil_image = self._overlay_text(pil_image)

            self.imgtk = ImageTk.PhotoImage(image=pil_image)
            self.canvas.delete('all')
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.imgtk)

        # update loggernet graph
        # if not self.loggernet.stop_event.is_set(): self.loggernet.update(0)
        # self.loggernet_canvas.draw_idle()
        # self.histogram.update(frame)
        # self.histogram_canvas.draw_idle()

        self.after(10, self.update_camera_feed)

    ## main functions for buttons ##
    @threaded
    def capture(self):
        """Capture an image when the button is pressed."""
        frame = self.camera.get_frame()
        if frame is not None:
            capture_image(frame)
            tkinter.messagebox.showinfo("Capture", "Image captured successfully.")
        else:
            tkinter.messagebox.showerror("Capture", "Failed to capture image.")

    def start_recording(self):
        """Start recording video."""
        if self.recording:
            tkinter.messagebox.showinfo("Recording",
                                        "Video is already recording.")
        else:
            self.recording = True

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"video_{timestamp}.avi"
            fourcc = cv2.VideoWriter.fourcc(*'XVID')
            self.video_writer = cv2.VideoWriter(filename, fourcc, CAMERA_FPS,
                                                (CAMERA_WIDTH, CAMERA_HEIGHT))
            tkinter.messagebox.showinfo("Recording",
                                        f"Video recording started: "
                                        f"{filename}\nPress SPACE to stop.")

    def stop_recording(self):
        """Stop recording video."""
        if self.recording:
            self.recording = False
            self.video_writer.release()
            tkinter.messagebox.showinfo("Recording", "Video recording stopped.")
        else:
            tkinter.messagebox.showinfo("Recording",
                                        "No video is currently recording.")

    def start_analysis(self):
        self.capture_task.start()
        self.observer_obj.start_monitoring()
        self.start_analysis_button.config(
            text="Stop Analysis",
            fg="darkred",
            command=self.stop_analysis
        )

    def stop_analysis(self):
        if self.capture_task.is_alive():
            self.capture_task.stop()
            self.capture_task.join()
        self.observer_obj.stop()
        self.start_analysis_button.config(
            text="Start Analysis",
            fg="darkgreen",
            command=self.start_analysis
        )
        self.capture_task = CaptureTask()
        self.observer_obj = src.analyzer.ObserverWrapper(self.analyzer,
                                                         self.sms_sender)

    def sms_info(self):
        sms_dialog = tk.Toplevel(self)
        sms_dialog.title("Enter SMS Details")
        sms_dialog.config(bg="white")

        # create label and checkbox for receiving messages
        receive_sms_var = tk.BooleanVar()
        receive_sms_label = tk.Label(sms_dialog,
                                     text="Would you like to receive text messages from a plant?",
                                     font=("TkTextFont", 18), bg="white")
        receive_sms_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        receive_sms_checkbox = tk.Checkbutton(sms_dialog,
                                              variable=receive_sms_var,
                                              bg="white")
        receive_sms_checkbox.grid(row=0, column=2, padx=10, pady=10)

        # create label and input for the name
        name_label = tk.Label(sms_dialog, text="Enter name: ",
                              font=("TkTextFont", 18), bg="white")
        name_label.grid(row=1, column=0, padx=10, pady=10)
        name_entry = tk.Entry(sms_dialog)
        name_entry.grid(row=1, column=1, padx=10, pady=10)

        # create label and input for the phone number
        contact_label = tk.Label(sms_dialog, text="Enter phone number: ",
                                 font=("TkTextFont", 18), bg="white")
        contact_label.grid(row=2, column=0, padx=10, pady=10)
        contact_entry = tk.Entry(sms_dialog, show="*")
        contact_entry.grid(row=2, column=1, padx=10, pady=10)

        # Label for displaying error messages
        error_label = tk.Label(sms_dialog, text="", fg="red",
                               font=("TkTextFont", 18), bg="white")
        error_label.grid(row=3, column=0, columnspan=2, padx=12, pady=10)

        def send_info():
            name = name_entry.get()
            contact = contact_entry.get()

            # Only set contact info if the checkbox is checked
            if receive_sms_var.get():
                if not name or not contact:
                    error_label.config(
                        text="Please provide a name and phone number.")
                else:
                    self.sms_sender.set_info(name, contact)
                    self.sms_sender.send_msg(
                        contact,
                        f"Hi {name}, it’s me, your plant Bob. Help, I’m trapped "
                        f"in this pot and they keep cutting off my leaves. "
                        f"Send more sunlight and water... or at least a funny "
                        f"meme. Don’t leaf me hanging!")
                    self.sms_sender.send_msg(contact, "🌿🌿🌿🌿🌿")
                    sms_dialog.destroy()
            else:
                error_label.config(
                    text="Please check the box and provide all details.")

        # Create Save button
        save_button = tk.Button(sms_dialog, text="Save", command=send_info)
        save_button.grid(row=4, column=0, padx=10, pady=10)

        # Create Cancel button
        cancel_button = tk.Button(sms_dialog, text="Cancel",
                                  command=sms_dialog.destroy)
        cancel_button.grid(row=4, column=1, padx=10, pady=10)

        image = tk.PhotoImage(
            file=BG_PATH)  # Change to the correct path to your image
        image_label = tk.Label(sms_dialog, image=image)
        image_label.grid(row=5, column=0, columnspan=2, padx=2,
                         pady=10)  # Place the image under the buttons
        image_label.image = image  # Keep a reference to the image to prevent it from being garbage collected

        sms_dialog.mainloop()

    @threaded
    def flash_leds(self):
        """Flash the LED when the button is pressed."""
        # TODO: Race condition with self._update_data
        self.microscope.Init()
        self.microscope.SetLEDState(0, 0)
        time.sleep(COMMAND_TIME)
        self.microscope.SetLEDState(0, 1)
        time.sleep(COMMAND_TIME)

    def show_exposure_dialog(self):
        def apply():
            value = exposure_entry.get()
            if self._validate_exposure(value):
                exposure_value = int(value)
                self._set_exposure(exposure_value)
                self.current_exposure = exposure_value
                dialog.destroy()
                (tkinter.messagebox
                 .showinfo("Exposure",
                           f"Exposure set to {exposure_value:,}"))
            else:
                error_label.config(
                    text="Please enter a valid value between 100 and 60,000")

        dialog = tk.Toplevel(self)
        dialog.title("Exposure Settings")
        dialog.geometry("400x200")
        dialog.resizable(False, False)

        content_frame = tk.Frame(dialog)
        content_frame.pack(expand=True, fill="both", padx=20, pady=20)

        current_label = tk.Label(content_frame,
                                 text=f"Current Exposure: {self.current_exposure:,}")
        current_label.pack(pady=(0, 10))

        input_frame = tk.Frame(content_frame)
        input_frame.pack(fill="x", pady=10)

        tk.Label(input_frame, text="New exposure (100-60,000):").pack(
            side="left")
        exposure_entry = tk.Entry(input_frame, width=10)
        exposure_entry.pack(side="left", padx=10)

        error_label = tk.Label(content_frame, text="", fg="red")
        error_label.pack(pady=5)

        button_frame = tk.Frame(content_frame)
        button_frame.pack()

        tk.Button(button_frame, text="Apply", command=apply, width=10).pack(
            side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                  width=10).pack(side="left", padx=5)

        exposure_entry.bind("<Return>", lambda e: apply())

        # Center the dialog on the main window
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (
                dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (
                dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    ## setup helpers ##
    def _animate_loading(self):
        """Animate the loading circle"""
        if hasattr(self, 'camera') and self.camera: return

        self.loading_canvas.delete("all")

        # Draw rotating arc
        # TODO: Bad loading icon
        self.loading_canvas.create_arc(5, 5, 45, 45, start=self.angle,
                                       extent=300, fill='',
                                       outline='blue', width=2)

        self.angle = (self.angle - 10) % 360
        self.after(50, self._animate_loading)

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

        # Capture Button
        self.capture_button = tk.Button(self.button_frame, text="Capture Image",
                                        command=self.capture)
        self.capture_button.pack(side="left", padx=10)

        # Start Recording Button
        self.start_record_button = tk.Button(self.button_frame,
                                             text="Start Recording",
                                             command=self.start_recording)
        self.start_record_button.pack(side="left", padx=10)

        # Stop Recording Button
        self.stop_record_button = tk.Button(self.button_frame,
                                            text="Stop Recording",
                                            command=self.stop_recording)
        self.stop_record_button.pack(side="left", padx=10)

        # Analysis buttons
        self.start_analysis_button = tk.Button(self.button_frame,
                                               text="Start Analysis",
                                               fg="darkgreen",
                                               command=self.start_analysis)
        self.start_analysis_button.pack(side="left", padx=10)

        # Set SMS information Button
        self.set_sms_button = tk.Button(self.button_frame, text="SMS Info",
                                        command=self.sms_info)
        self.set_sms_button.pack(side="left", padx=10)

        if self.microscope:
            # LED Flash Button
            self.flash_button = tk.Button(self.button_frame, text="Flash LEDs",
                                          command=self.flash_leds)
            self.flash_button.pack(side="left", padx=10)

            # Set exposure button
            self.exposure_button = tk.Button(self.button_frame,
                                             text="Exposure Settings",
                                             command=self.show_exposure_dialog)
            self.exposure_button.pack(side="left", padx=10)

        # Close Button
        self.quit_button = tk.Button(self.button_frame, text="Exit",
                                     command=self.quit)
        self.quit_button.pack(side="left", padx=10)

        # Bind events to handle canvas resizing
        self.button_frame.bind('<Configure>', on_frame_configure)
        self.button_canvas.bind('<Configure>', on_canvas_configure)

    def _get_microscope(self, dnx64_path):
        """Initialize microscope"""
        # try:
        #     self.microscope = DNX64(dnx64_path)
        # except FileNotFoundError:
        #     dnx64_path = (tkinter.simpledialog
        #                   .askstring("DNX64 Path",
        #                              "DNX64 file not found at"
        #                              f"\n{dnx64_path}.\n"
        #                              "Please enter your DNX64 path, or press "
        #                              "cancel to use a regular camera:"))
        #     if dnx64_path:
        #         self._get_microscope(dnx64_path)
        #     else:
        #         self.microscope = None
        #         (tkinter.messagebox
        #          .showinfo("DNX64 Path",
        #                    "DNX64 file not found, using a regular camera instead."))
        self.microscope = None

    @threaded
    def _init_camera_thread(self):
        """Initialize camera in a separate thread"""
        # if self.microscope:
        #     try:
        #         self.microscope.SetVideoDeviceIndex(DEVICE_INDEX)
        #         self.microscope.Init()
        #         self.current_exposure = self.microscope.GetExposureValue(
        #             DEVICE_INDEX)
        #     except OSError:
        #         print(
        #             "[DRIVER] Error: Video device not found. Please check your index.")
        #         sys.exit(1)

        # self.camera = cv2.VideoCapture(DEVICE_INDEX, cv2.CAP_DSHOW)
        # self.camera.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        # self.camera.set(cv2.CAP_PROP_FOURCC,
        #                 cv2.VideoWriter.fourcc('m', 'j', 'p', 'g'))
        # self.camera.set(cv2.CAP_PROP_FOURCC,
        #                 cv2.VideoWriter.fourcc('M', 'J', 'P', 'G'))
        # self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        # self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        self.after(0, self._setup_ui_after_camera)
        # self.after(0, self._update_data)

    def _load_watermark(self, watermark_path):
        """Load the watermark image and resize it."""

        def get_path(path):
            if path.exists():
                self.watermark = Image.open(watermark_path)
                self.watermark = self.watermark.resize((200, 100))
                # Pre-convert to RGBA
                if self.watermark.mode != 'RGBA':
                    self.watermark = self.watermark.convert('RGBA')
            else:
                self.watermark = Image.new("RGBA", (200, 100))

        get_path(watermark_path)

    def _setup_canvases(self):
        """Setup main canvas and graph canvases"""
        # Camera feed canvas
        self.canvas = tk.Canvas(self, width=WINDOW_WIDTH / 2,
                                height=WINDOW_HEIGHT)
        self.canvas.pack(side="left")

        # Loggernet graph canvas
        frame = tk.Frame(self)
        frame.pack(anchor="nw", padx=10, pady=10)
        self.loggernet_canvas = FigureCanvasTkAgg(self.loggernet.fig,
                                                  master=frame)
        self.loggernet_canvas.get_tk_widget().pack(anchor="nw")

        # Histogram canvas
        frame = tk.Frame(self)
        frame.pack(anchor="sw", padx=10, pady=10)
        self.histogram_canvas = FigureCanvasTkAgg(self.histogram.fig,
                                                  master=frame)
        self.histogram_canvas.get_tk_widget().pack(anchor="sw")

        self.imgtk = None  # Initialize a reference to avoid garbage collection

    def _setup_scroll_frame(self):
        """Setup scroll frame for buttons"""
        scroll_frame = tk.Frame(self)
        scroll_frame.pack(side="bottom", fill="x", pady=2)

        h_scrollbar = tk.Scrollbar(scroll_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")

        self.button_canvas = tk.Canvas(scroll_frame, height=30,
                                       xscrollcommand=h_scrollbar.set)
        self.button_canvas.pack(side="bottom", fill="x", pady=5)

        self.button_frame = tk.Frame(self.button_canvas)
        self.button_canvas.create_window((0, 0), window=self.button_frame,
                                         anchor="nw", tags="self.button_frame")
        h_scrollbar.config(command=self.button_canvas.xview)

    def _setup_ui_after_camera(self):
        """Setup UI after camera initialization"""
        # Remove loading screen
        self.loading_frame.destroy()

        # Continue with regular UI setup
        self.recording = False
        self.video_writer = None
        self.analyzing = False
        self.capture_task = CaptureTask()
        self.analyzer = src.analyzer.Analyzer()
        self.histogram = src.analyzer.Histogram()
        # self.sms_sender = src.sms_sender.SmsSender()
        self.loggernet = src.loggernet.Loggernet()
        # self.observer_obj = src.analyzer.ObserverWrapper(self.analyzer,
        #                                                  self.sms_sender)

        # Setup UI components
        self._setup_scroll_frame()
        self._setup_canvases()
        self._create_widgets()
        self._load_watermark(WATERMARK_PATH)
        self.imgtk = None

        # Start camera feed
        self.update_camera_feed()

    ## other helpers ##
    def _overlay_text(self, pil_image):
        """Overlay text in the northeast corner of the frame"""
        # Create a drawing object
        draw = ImageDraw.Draw(pil_image)

        try:
            text = f"AMR: {self.amr}x\nFOV: {self.fov} mm\nExposure: {self.current_exposure}"
            font = ImageFont.truetype("arial.ttf", 20)
            padding = 10

            # Draw white text in the red rectangle
            draw.text((padding, 150), text, fill='white',
                      font=font)

        finally:
            return pil_image

    def _overlay_watermark(self, frame):
        """Overlay the watermark on the frame."""
        # Convert the frame to RGB (from BGR)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert frame to a PIL image
        pil_image = Image.fromarray(frame_rgb)

        # Overlay watermark at bottom right corner (can change position)
        # watermark_width, watermark_height = self.watermark.size
        padding = 10
        pil_image.paste(
            self.watermark,
            (
                0 + padding,
                0 + padding,
            ),
            self.watermark,
        )
        return pil_image

    @threaded
    def _set_exposure(self, exposure):
        self.microscope.Init()
        self.microscope.SetAutoExposure(DEVICE_INDEX, 0)
        self.microscope.SetExposureValue(DEVICE_INDEX, exposure)
        time.sleep(QUERY_TIME)

    @threaded
    def _update_data(self):
        """Update the AMR and FOV values in background."""
        if self.microscope and self.camera and self.show_data:
            # TODO: Suppress print statements
            # TODO: amr is always 0
            self.microscope.Init()
            self.amr = round(self.microscope.GetAMR(DEVICE_INDEX), 1)
            self.fov = round(self.microscope.FOVx(
                DEVICE_INDEX, self.amr) / 1000, 2)
        self.after(500, self._update_data)

    def _validate_exposure(self, value):
        """Validate that the exposure value is between 100 and 60000."""
        try:
            value = int(value)
            if 100 <= value <= 60000:
                return True
            else:
                return False
        except ValueError:
            return False


def main():
    app = CameraApp()
    # threading.Thread(target=src.cutter_control.cutter_app).start()
    # app.update_camera_feed()  # Start the camera feed update loop
    app.mainloop()
