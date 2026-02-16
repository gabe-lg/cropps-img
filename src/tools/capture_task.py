import os
import shutil
import threading
import time

import cv2

# from driver_dnx64 import DNX64  # SDK wrapper from same folder

# Constants
DLL_PATH = r"C:\Users\17177\Desktop\research\cropps-img-headless\dino-lite-sdk\DNX64.dll"
DEVICE_INDEX = 0
EXPOSURE_VALUE = 3000  # Feel free to tweak this (range: 100–60000)

# the pictures from microscope are now saved in shared folder
# capture with the same frame rate of the camera
CAPTURE_INTERVAL = 0.5
# CAPTURE_INTERVAL = 2
FILE_LIMIT = 100000


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

    def __init__(self, camera, screenshot_directory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.camera = camera
        self.screenshot_directory = screenshot_directory
        self.image_counter = 0

    def run(self):
        print("[DRIVER] Capture thread started.")
        while not self.stopped():
            # if self.camera:
            # frame = self.camera.get_frame()
            # self.capture_image(frame)
            time.sleep(CAPTURE_INTERVAL)
        print("[DRIVER] Capture thread exiting...")

    def _delete_file(self):
        """Deletes all files in `SCREENSHOT_DIRECTORY` if file count is greater than FILE_LIMIT"""
        if os.path.exists(self.screenshot_directory):
            items = os.listdir(self.screenshot_directory)
            file_count = sum(1 for item in items if os.path.isfile(
                os.path.join(self.screenshot_directory, item)))
            if file_count >= FILE_LIMIT:
                for item in items:
                    item_path = os.path.join(self.screenshot_directory, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)

    def capture_image(self, frame):
        if not os.path.exists(self.screenshot_directory):
            os.makedirs(self.screenshot_directory)
        self._delete_file()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        counter_str = f"{self.image_counter:04d}"
        filename = os.path.join(self.screenshot_directory,
                                f"image_{counter_str}_{timestamp}.png")
        if frame is None or frame.size == 0:
            print(f"[ERROR] Invalid frame; skipping save to {filename}")
            return
        try:
            cv2.imwrite(filename, frame, [cv2.IMWRITE_PNG_COMPRESSION, 0])
            print(f"[DRIVER] Saved image to {filename}")
            self.image_counter += 1  # Increment after successful save
        except Exception as e:
            print(f"[ERROR] Failed to save image {filename}: {e}")

    def start_timer(self, dur, f):
        """ Sleeps for `dur` seconds then calls `f` """
        if not dur: return
        
        print(f"[DRIVER] timer spawned")
        for t in range(dur):
            time.sleep(1)
            if self.stopped():
                # account for delays when stopping manually
                time.sleep(1)
                break
        print(f"[DRIVER] timer stopped")
        f()


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
