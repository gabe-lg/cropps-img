import os
import threading
import time

import cv2

# Constants
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
        """Deletes oldest files in screenshot directory when count exceeds FILE_LIMIT."""
        if os.path.exists(self.screenshot_directory):
            files = [
                os.path.join(self.screenshot_directory, f)
                for f in os.listdir(self.screenshot_directory)
                if os.path.isfile(os.path.join(self.screenshot_directory, f))
            ]
            if len(files) >= FILE_LIMIT:
                files.sort(key=os.path.getctime)
                for f in files[:len(files) - FILE_LIMIT + 1]:
                    os.remove(f)

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

