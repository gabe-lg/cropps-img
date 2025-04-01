import cv2
import numpy as np
import time
import os
import platform
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

### PARAMETERS ###
# Change to your image directory (normalize slashes for platform!)
WATCH_DIR = ".\\CROPPS_Training_Dataset" if platform.system() == "Windows" else "./CROPPS_Training_Dataset"
PREFIX = ""
SHOW_IMG = False
FAILED = 0

# TOTAL INTENSITY
THRESHOLD_TOTAL_INTENSITY = 21000000

# MAX INTENSITY
THRESHOLD_MAX_INTENSITY = 100

# BRIGHT PIXELS
THRESHOLD_BRIGHT = 50
THRESHOLD_NUM_BRIGHT = 10

# BRIGHT PATCHES
AREA_H = 50
AREA_V = 50
THRESHOLD_PATCHES = 625
READ_DELAY = 1


### END OF PARAMETERS ###


def _detect(image_path, mask, extracted, criteria, desc) -> (bool, int):
    time.sleep(READ_DELAY)
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"[ANALYSIS] Error loading {image_path}")
        return False, None
    if SHOW_IMG and mask is not None:
        output = np.zeros_like(img)
        output[mask(img)] = img[mask(img)]
        cv2.imshow("High Intensity Pixels", output)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    data = extracted(img)
    agitated = criteria(data)
    print(f"[ANALYSIS] Processed: {image_path}")
    print(f"[ANALYSIS] {desc}: {data}")
    print(f"[ANALYSIS] Agitated: {agitated}\n")
    return agitated, data


def detect_brightness_total(image_path):
    return _detect(image_path, None, np.sum,
                   lambda extracted: extracted > THRESHOLD_TOTAL_INTENSITY,
                   "Total intensity")


def detect_yellow_num(image_path):
    return _detect(image_path, lambda img: img > THRESHOLD_BRIGHT,
                   lambda img: np.count_nonzero(img > THRESHOLD_BRIGHT),
                   lambda extracted: extracted > THRESHOLD_NUM_BRIGHT,
                   "Yellow pixels")


def detect_patch_of_yellow(image_path):
    def criterion(img):
        yellow_pixels = cv2.inRange(img, np.array([0]),
                                    np.array([THRESHOLD_BRIGHT])).tolist()
        count = 0
        for r in range(len(yellow_pixels)):
            for c in range(len(yellow_pixels[0])):
                if yellow_pixels[r][c]:
                    count_pixel = 0
                    for i in [n for n in range(-AREA_H // 2, AREA_H // 2)]:
                        for j in [n for n in range(-AREA_V // 2, AREA_V // 2)]:
                            try:
                                if yellow_pixels[r + i][c + j]:
                                    count_pixel += 1
                                    if count_pixel > THRESHOLD_PATCHES:
                                        break
                            except:
                                pass
                        if count_pixel > THRESHOLD_PATCHES:
                            break
                    if count_pixel > THRESHOLD_PATCHES:
                        count += 1
        return count

    return _detect(image_path, None, criterion,
                   lambda extracted: extracted > 0, "Yellow patches")


functions = [detect_yellow_num]


class ImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        file_name = os.path.basename(event.src_path)
        if file_name.startswith(PREFIX) and file_name.lower().endswith(
                ('.png', '.jpg', '.jpeg', '.tif')):
            p = event.src_path
            for i in range(len(functions)):
                functions[i](p)

class ObserverWrapper():
    def __init__(self):
        self.event_handler = ImageHandler()
        self.observer = Observer()
        # Set up file monitoring
        self.event_handler = ImageHandler()
        self.observer = Observer()

    def start_monitoring(self):
        print(f"Monitoring directory: {WATCH_DIR} for new images...")
        self.observer.schedule(self.event_handler, WATCH_DIR, recursive=False)
        self.observer.start()
    
    def stop(self):
        self.observer.stop()
        self.observer.join()

if __name__ == "__main__":
    observer_obj = ObserverWrapper()
    observer_obj.start_monitoring()
    
    def failed_count(failed, directory):
        files = os.listdir(WATCH_DIR + directory)
        count = [0 for _ in range(len(functions))]
        for file in files:
            p = os.path.join(WATCH_DIR + directory, file)
            if os.path.isfile(p):
                for i in range(len(functions)):
                    if functions[i](p)[0] == failed:
                        count[i] += 1
        return count


    # agitated_count = failed_count(False, '/agitated')
    # base_count = failed_count(True, '/base')
    # print(f"Failed count: {agitated_count}")
    # print(f"Failed count: {base_count}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer_obj.stop()
