import tkinter as tk
from tkinter import simpledialog
import threading
import time
import cv2
import os
import platform
from driver.dnx64 import DNX64
from analysis.main import ObserverWrapper, paint_square
from PIL import Image, ImageTk

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 960
CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS = 1280, 960, 30
DNX64_PATH = 'C:\\Program Files\\DNX64\\DNX64.dll'
DEVICE_INDEX = 0
QUERY_TIME = 0.05  # Buffer time for Dino-Lite to return value
COMMAND_TIME = 0.25  # Buffer time to allow Dino-Lite to process command
SCREENSHOT_DIRECTORY = ".\\CROPPS_Training_Dataset\\" if platform.system() == "Windows" else "./CROPPS_Training_Dataset/"

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

def capture_image(frame):
    """Capture an image and save it in the current working directory."""
    if not os.path.exists(SCREENSHOT_DIRECTORY):
        os.makedirs(SCREENSHOT_DIRECTORY)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = SCREENSHOT_DIRECTORY + f"image_{timestamp}.png"
    cv2.imwrite(filename, frame)
    print(f"[DRIVER] Saved image to {filename}")

def start_recording(frame_width, frame_height, fps):
    """Start recording video and return the video writer object."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"video_{timestamp}.avi"
    fourcc = cv2.VideoWriter.fourcc(*'XVID')
    video_writer = cv2.VideoWriter(filename, fourcc, fps, (frame_width, frame_height))
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
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('m','j','p','g'))
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M','J','P','G'))
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
        self.camera = initialize_camera()
        self.recording = False
        self.video_writer = None

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

        # Start Recording Button
        self.start_record_button = tk.Button(self.button_frame, text="Start Recording", command=self.start_recording)
        self.start_record_button.pack(side="left", padx=10)

        # Stop Recording Button
        self.stop_record_button = tk.Button(self.button_frame, text="Stop Recording", command=self.stop_recording)
        self.stop_record_button.pack(side="left", padx=10)

        # Close Button
        self.quit_button = tk.Button(self.button_frame, text="Exit", command=self.quit)
        self.quit_button.pack(side="left", padx=10)

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

    def update_camera_feed(self):
        """Update the camera feed in the GUI window."""
        ret, frame = self.camera.read()
        if ret:
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
