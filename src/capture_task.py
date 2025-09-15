import cv2
import os
import platform
import shutil
import threading
import time

SCREENSHOT_DIRECTORY = ".\\assets\\captured_data\\" if (
            platform.system() == "Windows") else "./assets/captured_data/"
CAPTURE_INTERVAL = 2
FILE_LIMIT = 10


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frame = None

    def run(self):
        if self.frame is None:
            raise Exception("Frame not set for capture")

        while not self.stopped():
            capture_image(self.frame)
            time.sleep(CAPTURE_INTERVAL)
        print("Exiting run...")

    def set_frame(self, frame):
        self.frame = frame

def _delete_file():
    """
    Deletes all files in `SCREENSHOT_DIRECTORY` if file count is greater than
     FILE_LIMIT
    """
    # Check if the folder exists
    if os.path.exists(SCREENSHOT_DIRECTORY):
        items = os.listdir(SCREENSHOT_DIRECTORY)
        file_count = sum(1 for item in items if os.path.isfile
                         (os.path.join(SCREENSHOT_DIRECTORY, item)))
        
        if file_count >= FILE_LIMIT:
            for item in items:
                item_path = os.path.join(SCREENSHOT_DIRECTORY, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)


def capture_image(frame):
    """Capture an image and save it in the current working directory."""
    # create image directory if it doesn't exist
    if not os.path.exists(SCREENSHOT_DIRECTORY):
        os.makedirs(SCREENSHOT_DIRECTORY)

    _delete_file()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = SCREENSHOT_DIRECTORY + f"image_{timestamp}.png"
    cv2.imwrite(filename, frame)
    print(f"[DRIVER] Saved image to {filename}")
