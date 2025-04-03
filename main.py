import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox
import threading
import time
import cv2
import analysis.main
from pathlib import Path
from driver.dnx64 import DNX64
from capture_task import capture_image, CaptureTask
from PIL import Image, ImageTk
import send_sms

# Paths
WATERMARK_PATH = Path(__file__).parent / "assets" / "cropps_watermark.png"
ICO_PATH = Path(__file__).parent / "assets" / "CROPPS_vertical_logo.png"
DNX64_PATH = 'C:\\Users\\CROPPS-in-Box\\Documents\\cropps main folder\\DNX64\\DNX64.dll'

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 1400, 960
CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS = 1400, 960, 30
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
        self.iconphoto(False, tk.PhotoImage(file=ICO_PATH))
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
        self.observer_obj = analysis.main.ObserverWrapper()

        # Create a frame for buttons to be packed into
        self.button_frame = tk.Frame(self)
        self.button_frame.pack(side="bottom", pady=10)

        # Create a canvas for displaying the camera feed
        self.canvas = tk.Canvas(self, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        self.canvas.pack()

        self.create_widgets()

        self.load_watermark(WATERMARK_PATH)
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
        self.start_analysis_button = tk.Button(self.button_frame, text="Start Analysis", fg="darkgreen", command=self.start_analysis)
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

        # Set SMS information Button
        self.set_sms_button = tk.Button(self.button_frame, text="SMS Info", command=self.sms_info)
        self.set_sms_button.pack(side="left", padx=10)

        # Close Button
        self.quit_button = tk.Button(self.button_frame, text="Exit", command=self.quit)
        self.quit_button.pack(side="left", padx=10)

    def sms_info(self):
        sms_dialog = tk.Toplevel(self)
        sms_dialog.title("Enter SMS Details")

        #create label and input for the name 
        name_label = tk.Label(sms_dialog, text="Enter name: ")
        name_label.grid(row=0, column=0, padx=10, pady=10)
        name_entry = tk.Entry(sms_dialog)
        name_entry.grid(row=0, column=1, padx=10, pady=10)

        #create label and input for the phone number  
        contact_label = tk.Label(sms_dialog, text="Enter phone number: ")
        contact_label.grid(row=1, column=0, padx=10, pady=10)
        contact_entry = tk.Entry(sms_dialog)
        contact_entry.grid(row=1, column=1, padx=10, pady=10)

        def send_info():
            name = name_entry.get()
            contact = contact_entry.get()

            if name and contact:
                  send_sms.set_info(name, contact)
                  sms_dialog.destroy()
            else:
                print("Both values are required")
       
        #create a save button 
        save_button = tk.Button(sms_dialog, text="Save", command=send_info)
        save_button.grid(row=2, columnspan=2, pady=10)

      

        sms_dialog.mainloop()
        
        
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
            print(f"[DRIVER] Warning: Watermark file not found at {watermark_path}")
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
            self.video_writer = start_recording(CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS)

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
        self.observer_obj = analysis.main.ObserverWrapper()

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
            self.exposure_label_text.set(f"Set Exposure (100 - 60,000, Current: {self.current_exposure:,}):")
            print(f"Exposure set to {exposure_value:,}")
        self.set_exposure_loading(False)

    def update_camera_feed(self):
        """Update the camera feed in the GUI window."""
        ret, frame = self.camera.read()
        if ret:
            self.capture_task.set_frame(frame)
            frame_with_watermark = self.overlay_watermark(frame)
            self.imgtk = ImageTk.PhotoImage(image=frame_with_watermark)
            self.canvas.delete('all')
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.imgtk)

        # Update every 10 ms
        self.after(10, self.update_camera_feed)

def main():
    app = CameraApp()
    app.update_camera_feed()  # Start the camera feed update loop
    app.mainloop()

if __name__ == "__main__":
    main()
