import cv2
import threading
import time
import tkinter as tk
import src.analyzer
import src.cutter_control
import src.loggernet
from pathlib import Path
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from src.capture_task import capture_image, CaptureTask
from src.driver_dnx64 import DNX64

# Paths
WATERMARK_PATH = Path(__file__).parent.parent / "assets" / "cropps_watermark.png"
ICO_PATH = "./assets/CROPPS_vertical_logo.png"
BG_PATH = Path(__file__).parent.parent / "assets" / "cropps_background.png"
DNX64_PATH = 'C:\\Users\\CROPPS-in-Box\\Documents\\cropps main folder\\DNX64\\DNX64.dll'

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 1600, 900
CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS = 1280, 960, 30
DEVICE_INDEX = 0
QUERY_TIME = 0.05  # Buffer time for Dino-Lite to return value
COMMAND_TIME = 0.25  # Buffer time to allow Dino-Lite to process command


def threaded(func):
    """Wrapper to run a function in a separate thread with @threaded decorator"""

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()

    return wrapper


# Initialize microscope
microscope = DNX64(DNX64_PATH)


def set_exposure(exposure):
    microscope.Init()
    microscope.SetAutoExposure(DEVICE_INDEX, 0)
    microscope.SetExposureValue(DEVICE_INDEX, exposure)
    time.sleep(QUERY_TIME)


def start_recording(frame_width, frame_height, fps):
    """Start recording video and return the video writer object."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"video_{timestamp}.avi"
    fourcc = cv2.VideoWriter.fourcc(*'XVID')
    video_writer = cv2.VideoWriter(filename, fourcc, fps,
                                   (frame_width, frame_height))
    print(f"Video recording started: {filename}\nPress SPACE to stop.")
    return video_writer


def stop_recording(video_writer):
    """Stop recording video and release the video writer object."""
    video_writer.release()
    print("Video recording stopped")


def initialize_camera():
    """Setup OpenCV camera parameters and return the camera object."""
    camera = cv2.VideoCapture(DEVICE_INDEX, cv2.CAP_DSHOW)
    camera.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('m', 'j', 'p', 'g'))
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M', 'J', 'P', 'G'))
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    return camera


def process_frame(frame):
    """Resize frame to fit window."""
    return cv2.resize(frame, (WINDOW_WIDTH, WINDOW_HEIGHT))


class CameraApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CROPPS Camera Control")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.icon = tk.PhotoImage(file=ICO_PATH)
        self.iconphoto(False, self.icon)
        # self.iconphoto(False, ICO_PATH)

        microscope.SetVideoDeviceIndex(
            DEVICE_INDEX)  # Set index of video device. Call before Init().
        microscope.Init()  # Initialize the control object. Required before using other methods, otherwise return values will fail or be incorrect.
        self.current_exposure = microscope.GetExposureValue(DEVICE_INDEX)
        self.camera = initialize_camera()

        self.recording = False
        self.video_writer = None
        self.analyzing = False
        self.capture_task = CaptureTask()
        self.analyzer = src.analyzer.Analyzer()
        self.histogram = src.analyzer.Histogram()
        self.sms_sender = src.sms_sender.SmsSender()
        self.loggernet = src.loggernet.Loggernet()
        self.observer_obj = src.analyzer.ObserverWrapper(self.analyzer,
                                                         self.sms_sender)

        # Create a frame for buttons to be packed into
        self.button_frame = tk.Frame(self)
        self.button_frame.pack(side="bottom", pady=10)

        # Create a canvas for displaying the camera feed
        self.canvas = tk.Canvas(self, width=WINDOW_WIDTH / 2, height=WINDOW_HEIGHT)
        self.canvas.pack(side="left")

        # Create a canvas for displaying the loggernet graph

        frame = tk.Frame(self)
        frame.pack(anchor="nw", padx=10, pady=10)
        self.loggernet_canvas = FigureCanvasTkAgg(self.loggernet.fig, master=frame)
        self.loggernet_canvas.get_tk_widget().pack(anchor="nw")

        frame = tk.Frame(self)
        frame.pack(anchor="sw", padx=10, pady=10)
        self.histogram_canvas = FigureCanvasTkAgg(self.histogram.fig, master=frame)
        self.histogram_canvas.get_tk_widget().pack(anchor="sw")

        self.create_widgets()

        self.load_watermark(WATERMARK_PATH)
        self.imgtk = None  # Initialize a reference to avoid garbage collection

    def create_widgets(self):
        """Create all the GUI buttons."""
        # AMR Button
        self.amr_button = tk.Button(self.button_frame, text="Print AMR",
                                    command=self.print_amr)
        self.amr_button.pack(side="left", padx=10)

        # LED Flash Button
        self.flash_button = tk.Button(self.button_frame, text="Flash LEDs",
                                      command=self.flash_leds)
        self.flash_button.pack(side="left", padx=10)

        # FOV Button
        self.fov_button = tk.Button(self.button_frame, text="Print FOV (mm)",
                                    command=self.print_fov)
        self.fov_button.pack(side="left", padx=10)

        # Capture Button
        self.capture_button = tk.Button(self.button_frame, text="Capture Image",
                                        command=self.capture)
        self.capture_button.pack(side="left", padx=10)

        # Analysis buttons
        self.start_analysis_button = tk.Button(self.button_frame,
                                               text="Start Analysis",
                                               fg="darkgreen",
                                               command=self.start_analysis)
        self.start_analysis_button.pack(side="left", padx=10)

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

        # Show Histogram Button
        self.show_hist_button = tk.Button(self.button_frame,
                                          text="Show Histogram",
                                          command=self.show_hist)
        self.show_hist_button.pack(side="left", padx=10)

        # Exposure label and entry
        self.exposure_label_text = tk.StringVar(
            value=f"Set Exposure (100 - 60,000, Current: {self.current_exposure:,}):")
        self.exposure_label = tk.Label(self.button_frame,
                                       textvariable=self.exposure_label_text)
        self.exposure_label.pack(side="left", padx=10)

        self.exposure_entry = tk.Entry(self.button_frame)
        self.exposure_entry.pack(side="left", padx=10)
        self.exposure_entry.bind("<Return>",
                                 lambda event: self.apply_exposure())

        # Set Exposure Button
        self.set_exposure_button = tk.Button(self.button_frame,
                                             text="Set Exposure",
                                             command=self.apply_exposure)
        self.set_exposure_button.pack(side="left", padx=10)

        # Set SMS information Button
        self.set_sms_button = tk.Button(self.button_frame, text="SMS Info",
                                        command=self.sms_info)
        self.set_sms_button.pack(side="left", padx=10)

        # Close Button
        self.quit_button = tk.Button(self.button_frame, text="Exit",
                                     command=self.quit)
        self.quit_button.pack(side="left", padx=10)

    def sms_info(self):
        sms_dialog = tk.Toplevel(self)
        sms_dialog.title("Enter SMS Details")
        sms_dialog.config(bg="white")

        # create label and checkbox for receiving messages
        receive_sms_var = tk.BooleanVar()
        receive_sms_label = tk.Label(sms_dialog, text="Would you like to receive text messages from a plant?",
                                     font=("TkTextFont", 18), bg="white")
        receive_sms_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        receive_sms_checkbox = tk.Checkbutton(sms_dialog, variable=receive_sms_var, bg="white")
        receive_sms_checkbox.grid(row=0, column=2, padx=10, pady=10)

        # create label and input for the name
        name_label = tk.Label(sms_dialog, text="Enter name: ", font=("TkTextFont", 18), bg="white")
        name_label.grid(row=1, column=0, padx=10, pady=10)
        name_entry = tk.Entry(sms_dialog)
        name_entry.grid(row=1, column=1, padx=10, pady=10)

        # create label and input for the phone number
        contact_label = tk.Label(sms_dialog, text="Enter phone number: ", font=("TkTextFont", 18), bg="white")
        contact_label.grid(row=2, column=0, padx=10, pady=10)
        contact_entry = tk.Entry(sms_dialog, show="*")
        contact_entry.grid(row=2, column=1, padx=10, pady=10)

        # Label for displaying error messages
        error_label = tk.Label(sms_dialog, text="", fg="red", font=("TkTextFont", 18), bg="white")
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
        image_label.grid(row=5, column=0, columnspan=2, padx=2, pady=10)  # Place the image under the buttons
        image_label.image = image  # Keep a reference to the image to prevent it from being garbage collected

        sms_dialog.mainloop()

    def show_hist(self):
        ret, frame = self.camera.read()
        if ret:
            self.analyzer.plot_histogram(frame)

    def quit(self):
        cv2.destroyAllWindows()
        self.stop_analysis()
        self.camera.release()
        super().quit()

    def load_watermark(self, watermark_path):
        """Load the watermark image and resize it."""
        if watermark_path.exists():  # Check if the watermark file exists
            self.watermark = Image.open(watermark_path)
            self.watermark = self.watermark.resize(
                (200, 100)
            )  # Resize the watermark (optional)
        else:
            print(
                f"[DRIVER] Warning: Watermark file not found at {watermark_path}")
            self.watermark = Image.new(
                "RGBA", (200, 100)
            )  # Return an empty image if the watermark doesn't exist

    def overlay_watermark(self, frame):
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
    def capture(self):
        """Capture an image when the button is pressed."""
        ret, frame = self.camera.read()
        if ret:
            capture_image(frame)

    @threaded
    def print_amr(self):
        """Print the AMR value when the button is pressed."""
        microscope.Init()
        amr = microscope.GetAMR(DEVICE_INDEX)
        amr = round(amr, 1)
        print(f"{amr}x")

    @threaded
    def flash_leds(self):
        """Flash the LED when the button is pressed."""
        microscope.Init()
        microscope.SetLEDState(0, 0)
        time.sleep(COMMAND_TIME)
        microscope.SetLEDState(0, 1)
        time.sleep(COMMAND_TIME)

    @threaded
    def print_fov(self):
        """Print the FOV in mm when the button is pressed."""
        microscope.Init()
        fov = microscope.FOVx(DEVICE_INDEX, microscope.GetAMR(DEVICE_INDEX))
        fov = round(fov / 1000, 2)
        print(f"{fov} mm")

    def start_recording(self):
        """Start recording video."""
        if not self.recording:
            self.recording = True
            self.video_writer = start_recording(CAMERA_WIDTH, CAMERA_HEIGHT,
                                                CAMERA_FPS)

    def stop_recording(self):
        """Stop recording video."""
        if self.recording:
            self.recording = False
            self.video_writer.release()

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

    def validate_exposure(self, value):
        """Validate that the exposure value is between 100 and 60000."""
        try:
            value = int(value)
            if 100 <= value <= 60000:
                return True
            else:
                return False
        except ValueError:
            return False

    # UI feature to display when waiting for microscope
    def set_exposure_loading(self, status):
        if status is True:
            self.set_exposure_button.config(
                state="disabled",
                text="Working..."
            )
        else:
            self.set_exposure_button.config(
                state="normal",
                text="Set Exposure"
            )

    @threaded
    def apply_exposure(self):
        """Apply the exposure value to the microscope."""
        self.set_exposure_loading(True)
        exposure_value = self.exposure_entry.get()
        if self.validate_exposure(exposure_value):
            exposure_value = int(exposure_value)
            set_exposure(exposure_value)
            self.current_exposure = exposure_value
            self.exposure_label_text.set(
                f"Set Exposure (100 - 60,000, Current: {self.current_exposure:,}):")
            print(f"Exposure set to {exposure_value:,}")
        self.set_exposure_loading(False)

    def update_camera_feed(self):
        """Update the camera feed in the GUI window."""
        ret, frame = self.camera.read()
        if ret:
            self.capture_task.set_frame(frame)
            self.analyzer.paint_square(frame)
            frame_with_watermark = self.overlay_watermark(frame)
            self.imgtk = ImageTk.PhotoImage(image=frame_with_watermark)
            self.canvas.delete('all')
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.imgtk)

        # update loggernet graph
        self.loggernet.update(0)  # updates the data, changes plot
        self.loggernet_canvas.draw_idle() if self.loggernet_canvas else print("loggernet is none")
        self.histogram.update(frame)
        self.histogram_canvas.draw_idle() if self.histogram_canvas else print("histogram is none")

        # Update every 10 ms
        self.after(50, self.update_camera_feed)


def main():
    threading.Thread(target=src.cutter_control.cutter_app).start()
    app = CameraApp()
    app.update_camera_feed()  # Start the camera feed update loop
    app.mainloop()
