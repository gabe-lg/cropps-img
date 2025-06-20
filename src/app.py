import cv2
import threading
import time
import tkinter as tk
import tkinter.simpledialog, tkinter.messagebox
import src.analyzer
import src.cutter_control
import src.loggernet
import sys
from pathlib import Path
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from src.capture_task import capture_image, CaptureTask
from src.driver_dnx64 import DNX64

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


def threaded(func):
    """Wrapper to run a function in a separate thread with @threaded decorator"""

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()

    return wrapper


def get_microscope(dnx64_path):
    """Initialize microscope"""
    global microscope
    try:
        microscope = DNX64(dnx64_path)
    except FileNotFoundError:
        dnx64_path = (tkinter.simpledialog
                      .askstring("DNX64 Path",
                                 "DNX64 file not found at"
                                 f"\n{dnx64_path}.\n"
                                 "Please enter your DNX64 path, or press "
                                 "cancel to use a regular camera:"))
        if dnx64_path:
            get_microscope(dnx64_path)
        else:
            microscope = None
            (tkinter.messagebox
             .showinfo("DNX64 Path",
                       "DNX64 file not found, using a regular camera instead."))


get_microscope(DNX64_PATH)


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

        if microscope:
            try:
                microscope.SetVideoDeviceIndex(
                    DEVICE_INDEX)  # Set index of video device. Call before Init().
            except OSError:
                print(
                    "[DRIVER] Error: Video device not found. Please check your index.")
                sys.exit(1)

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

        # For buttons
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

        # Create a canvas for displaying the camera feed
        self.canvas = tk.Canvas(self, width=WINDOW_WIDTH / 2,
                                height=WINDOW_HEIGHT)
        self.canvas.pack(side="left")

        # Create a canvas for displaying the loggernet graph
        frame = tk.Frame(self)
        frame.pack(anchor="nw", padx=10, pady=10)
        self.loggernet_canvas = FigureCanvasTkAgg(self.loggernet.fig,
                                                  master=frame)
        self.loggernet_canvas.get_tk_widget().pack(anchor="nw")

        frame = tk.Frame(self)
        frame.pack(anchor="sw", padx=10, pady=10)
        self.histogram_canvas = FigureCanvasTkAgg(self.histogram.fig,
                                                  master=frame)
        self.histogram_canvas.get_tk_widget().pack(anchor="sw")

        self.create_widgets()

        self.load_watermark(WATERMARK_PATH)
        self.imgtk = None  # Initialize a reference to avoid garbage collection

    def create_widgets(self):
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

        # # Show Histogram Button
        # self.show_hist_button = tk.Button(self.button_frame,
        #                                   text="Show Histogram",
        #                                   command=self.show_hist)
        # self.show_hist_button.pack(side="left", padx=10)

        # Set SMS information Button
        self.set_sms_button = tk.Button(self.button_frame, text="SMS Info",
                                        command=self.sms_info)
        self.set_sms_button.pack(side="left", padx=10)

        if microscope:
            # AMR Button
            self.amr_button = tk.Button(self.button_frame, text="Print AMR",
                                        command=self.print_amr)
            self.amr_button.pack(side="left", padx=10)

            # LED Flash Button
            self.flash_button = tk.Button(self.button_frame, text="Flash LEDs",
                                          command=self.flash_leds)
            self.flash_button.pack(side="left", padx=10)

            # FOV Button
            self.fov_button = tk.Button(self.button_frame,
                                        text="Print FOV (mm)",
                                        command=self.print_fov)
            self.fov_button.pack(side="left", padx=10)

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

    # def show_hist(self):
    #     ret, frame = self.camera.read()
    #     if ret:
    #         self.analyzer.plot_histogram(frame)

    def quit(self):
        print("Exiting...")
        self.stop_analysis()
        self.camera.release()
        self.destroy()
        super().quit()

    def load_watermark(self, watermark_path):
        """Load the watermark image and resize it."""

        def get_path(path):
            if path.exists():  # Check if the watermark file exists
                self.watermark = Image.open(watermark_path)
                self.watermark = self.watermark.resize(
                    (200, 100)
                )  # Resize the watermark (optional)
            else:
                path = tkinter.simpledialog.askstring("Watermark",
                                                      "Watermark file not found at"
                                                      f"\n{path}.\n"
                                                      "Please enter a valid path, or press cancel to skip:")
                if path:
                    get_path(Path(path))
                else:
                    self.watermark = Image.new(
                        "RGBA", (200, 100)
                    )  # Return an empty image if the watermark doesn't exist
                    tkinter.messagebox.showinfo(
                        "Watermark",
                        "Watermark file not found. Using an empty image instead."
                    )

        get_path(watermark_path)

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

    def show_exposure_dialog(self):
        def apply():
            value = exposure_entry.get()
            if self.validate_exposure(value):
                exposure_value = int(value)
                set_exposure(exposure_value)
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
        if not self.loggernet.stop_event.is_set(): self.loggernet.update(0)
        self.loggernet_canvas.draw_idle() if self.loggernet_canvas else print(
            "loggernet is none")
        self.histogram.update(frame)
        self.histogram_canvas.draw_idle() if self.histogram_canvas else print(
            "histogram is none")

        # Update every 10 ms
        self.after(50, self.update_camera_feed)


def main():
    app = CameraApp()
    threading.Thread(target=src.cutter_control.cutter_app).start()
    app.update_camera_feed()  # Start the camera feed update loop
    app.mainloop()
