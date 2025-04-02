import tkinter as tk
from tkinter import simpledialog
import threading
import time
import cv2
from driver.dnx64 import DNX64
from analysis.main import ObserverWrapper, paint_square
from capture_task import capture_image, CaptureTask
from PIL import Image, ImageTk

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 960
CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS = 1280, 960, 30
DNX64_PATH = 'C:\\Program Files\\DNX64\\DNX64.dll'
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
        self.title("Dino-Lite Camera Control")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        microscope.SetVideoDeviceIndex(
        DEVICE_INDEX)  # Set index of video device. Call before Init().
        microscope.Init()  # Initialize the control object. Required before using other methods, otherwise return values will fail or be incorrect.
        self.current_exposure = microscope.GetExposureValue(DEVICE_INDEX)
        self.camera = initialize_camera()
        self.recording = False
        self.video_writer = None
        self.analyzing = False
        self.capture_task = CaptureTask()
        self.observer_obj = ObserverWrapper()

        # Create a frame for buttons to be packed into
        self.button_frame = tk.Frame(self)
        self.button_frame.pack(side="bottom", pady=10)

        # Create a canvas for displaying the camera feed
        self.canvas = tk.Canvas(self, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        self.canvas.pack()

        self.create_widgets()

        self.imgtk = None  # Initialize a reference to avoid garbage collection

    def create_widgets(self):
        """Create all the GUI buttons."""
        # AMR Button
        self.amr_button = tk.Button(self.button_frame, text="Print AMR", command=self.print_amr)
        self.amr_button.pack(side="left", padx=10)

        # LED Flash Button
        self.flash_button = tk.Button(self.button_frame, text="Flash LEDs", command=self.flash_leds)
        self.flash_button.pack(side="left", padx=10)

        # FOV Button
        self.fov_button = tk.Button(self.button_frame, text="Print FOV (mm)", command=self.print_fov)
        self.fov_button.pack(side="left", padx=10)

        # Capture Button
        self.capture_button = tk.Button(self.button_frame, text="Capture Image", command=self.capture)
        self.capture_button.pack(side="left", padx=10)

        # Analysis buttons
        self.start_analysis_button = tk.Button(self.button_frame, text="Start Analsysis", fg="darkgreen", command=self.start_analysis)
        self.start_analysis_button.pack(side="left", padx=10)

        # Start Recording Button
        self.start_record_button = tk.Button(self.button_frame, text="Start Recording", command=self.start_recording)
        self.start_record_button.pack(side="left", padx=10)

        # Stop Recording Button
        self.stop_record_button = tk.Button(self.button_frame, text="Stop Recording", command=self.stop_recording)
        self.stop_record_button.pack(side="left", padx=10)

        # Exposure label and entry
        self.exposure_label_text = tk.StringVar(value=f"Set Exposure (100 - 60,000, Current: {self.current_exposure:,}):")
        self.exposure_label = tk.Label(self.button_frame, textvariable=self.exposure_label_text)
        self.exposure_label.pack(side="left", padx=10)

        self.exposure_entry = tk.Entry(self.button_frame)
        self.exposure_entry.pack(side="left", padx=10)
        self.exposure_entry.bind("<Return>", lambda event: self.apply_exposure())

        # Set Exposure Button
        self.set_exposure_button = tk.Button(self.button_frame, text="Set Exposure", command=self.apply_exposure)
        self.set_exposure_button.pack(side="left", padx=10)

        # Close Button
        self.quit_button = tk.Button(self.button_frame, text="Exit", command=self.quit)
        self.quit_button.pack(side="left", padx=10)

    def quit(self):
        cv2.destroyAllWindows()
        self.stop_analysis()
        self.camera.release()
        super().quit()

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
            self.video_writer = start_recording(CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS)

    def stop_recording(self):
        """Stop recording video."""
        if self.recording:
            self.recording = False
            stop_recording(self.video_writer)

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
        self.observer_obj = ObserverWrapper()

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

    def apply_exposure(self):
        """Apply the exposure value to the microscope."""
        exposure_value = self.exposure_entry.get()
        if self.validate_exposure(exposure_value):
            exposure_value = int(exposure_value)
            set_exposure(exposure_value)
            self.current_exposure = exposure_value
            self.exposure_label_text.set(f"Set Exposure (100 - 60,000, Current: {self.current_exposure:,}):")
            print(f"Exposure set to {exposure_value:,}")

    def update_camera_feed(self):
        """Update the camera feed in the GUI window."""
        ret, frame = self.camera.read()
        if ret:
            self.capture_task.set_frame(frame)
            # Convert the frame to RGB (from BGR)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Convert the frame to a PIL image
            img = Image.fromarray(frame_rgb)
            # Convert the PIL image to a Tkinter image
            self.imgtk = ImageTk.PhotoImage(image=img)
            # Update the canvas with the new image
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.imgtk)

        # Update every 10 ms
        self.after(10, self.update_camera_feed)

def main():
    app = CameraApp()
    app.update_camera_feed()  # Start the camera feed update loop
    app.mainloop()

if __name__ == "__main__":
    main()
