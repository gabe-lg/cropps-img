import cv2
import os
import platform
import shutil
import threading
import time

from driver_dnx64 import DNX64  # SDK wrapper from same folder

# Constants
DLL_PATH = r"C:\Users\17177\Desktop\research\cropps-img-headless\dino-lite-sdk\DNX64.dll"
DEVICE_INDEX = 0
EXPOSURE_VALUE = 3000  # Feel free to tweak this (range: 100–60000)

# the pictures from microscope are now saved in shared folder
SCREENSHOT_DIRECTORY = os.environ.get(
    "CAPTURE_DIR",
    r"C:\Users\17177\Desktop\cropps-img-half\cropps-img\shared-images"
)
CAPTURE_INTERVAL = 2
FILE_LIMIT = 200


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
        print("[DRIVER] Capture thread started.")

        # === SET EXPOSURE USING SDK ===
        try:
            dino = DNX64(DLL_PATH)
            if dino.Init():
                dino.SetVideoDeviceIndex(DEVICE_INDEX)
                dino.SetAutoExposure(DEVICE_INDEX, 0)  # Manual mode
                dino.SetExposureValue(DEVICE_INDEX, EXPOSURE_VALUE)
                print(f"[DRIVER] Exposure set to {EXPOSURE_VALUE} via SDK.")
            else:
                print("[DRIVER] Dino SDK failed to initialize. Skipping exposure config.")
        except Exception as e:
            print(f"[DRIVER] SDK Error: {e}")
            print("[DRIVER] Continuing with default exposure settings.")

        # Start camera
        self.cam = cv2.VideoCapture(DEVICE_INDEX, cv2.CAP_DSHOW)  # DSHOW preferred for Dino
        if not self.cam.isOpened():
            raise Exception("Could not open Dino Lite camera")

        while not self.stopped():
            ret, frame = self.cam.read()
            if not ret:
                print("[DRIVER] Failed to grab frame")
                continue

            capture_image(frame)
            time.sleep(CAPTURE_INTERVAL)

        self.cam.release()
        print("[DRIVER] Capture thread exiting...")


def _delete_file():
    """Deletes all files in `SCREENSHOT_DIRECTORY` if file count is greater than FILE_LIMIT"""
    if os.path.exists(SCREENSHOT_DIRECTORY):
        items = os.listdir(SCREENSHOT_DIRECTORY)
        file_count = sum(1 for item in items if os.path.isfile(os.path.join(SCREENSHOT_DIRECTORY, item)))
        if file_count >= FILE_LIMIT:
            for item in items:
                item_path = os.path.join(SCREENSHOT_DIRECTORY, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)


def capture_image(frame):
    """Capture an image and save it in the current working directory."""
    if not os.path.exists(SCREENSHOT_DIRECTORY):
        os.makedirs(SCREENSHOT_DIRECTORY)

    _delete_file()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(SCREENSHOT_DIRECTORY, f"image_{timestamp}.png")
    cv2.imwrite(filename, frame)
    print(f"[DRIVER] Saved image to {filename}")


# run the code only if this script is executed directly 
if __name__ == "__main__":
    task = CaptureTask()
    task.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping capture...")
        task.stop()
        task.join()