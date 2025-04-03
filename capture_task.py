import time
import os
import threading
import platform
import cv2

SCREENSHOT_DIRECTORY = ".\\captured_data\\" if platform.system() == "Windows" else "./captured_data/"
CAPTURE_INTERVAL = 2

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

class CaptureTask(StoppableThread):
    """Thread that captures an image every `CAPTURE_INTERVAL` seconds."""
    frame = None

    def run(self):
        if self.frame is None:
            raise Exception("Frame not set for capture")

        while not self.stopped():
            capture_image(self.frame)
            time.sleep(CAPTURE_INTERVAL)
        print("Exiting run...")

    def set_frame(self, frame):
        self.frame = frame

def capture_image(frame):
    """Capture an image and save it in the current working directory."""
    # create image directory if it doesn't exist
    if not os.path.exists(SCREENSHOT_DIRECTORY):
        os.makedirs(SCREENSHOT_DIRECTORY)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = SCREENSHOT_DIRECTORY + f"image_{timestamp}.png"
    cv2.imwrite(filename, frame)
    print(f"[DRIVER] Saved image to {filename}")