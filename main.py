import cv2
import numpy as np
import time
import os
import matplotlib.pyplot as plt
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Parameters
WATCH_DIR = "./CROPPS_Training_Dataset"  # Change to your image directory
THRESHOLD = 1e7  # Adjust based on image intensity range
PREFIX = ""


def _detect(image_path, img, extracted, criteria, desc) -> (bool, int):
    if img is None:
        print(f"Error loading {image_path}")
        return False, None
    data = extracted(img)
    agitated = criteria(data)
    print(f"Processed: {image_path}")
    print(f"{desc}: {data}")
    print(f"Agitated: {agitated}\n")
    return agitated, data


def detect_brightness_total(image_path):
    return _detect(image_path, cv2.imread(image_path, cv2.IMREAD_GRAYSCALE),
                   lambda img: np.sum(img),
                   lambda extracted: extracted > 21000000, "Total intensity")


def detect_hue_max(image_path):
    return _detect(image_path,
                   cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_RGB2HSV),
                   lambda img: np.min(abs(img[:, :, 0] - 30)),
                   lambda extracted: extracted < 100, "Max hue")


def detect_yellow_num(image_path):
    return _detect(image_path,
                   cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_RGB2HSV),
                   lambda img: cv2.countNonZero(
                       cv2.inRange(img[:, :, 0], np.array([0]),
                                   np.array([120]))),
                   lambda extracted: extracted > 10, "Yellow pixels")


def detect_patch_of_yellow(image_path):
    def criterion(img):
        ## parameters ##
        area_r = 50
        area_c = 50
        threshold = 625

        yellow_pixels = cv2.inRange(img[:, :, 0], np.array([0]),
                                    np.array([120])).tolist()
        count = 0
        for r in range(len(yellow_pixels)):
            for c in range(len(yellow_pixels[0])):
                if yellow_pixels[r][c]:
                    count_pixel = 0
                    for i in [n for n in range(-area_r // 2, area_r // 2)]:
                        for j in [n for n in range(-area_c // 2, area_c // 2)]:
                            try:
                                if yellow_pixels[r + i][c + j]:
                                    count_pixel += 1
                                    if count_pixel > threshold:
                                        break
                            except:
                                pass
                        if count_pixel > threshold:
                            break
                    if count_pixel > threshold:
                        count += 1
        return count

    return _detect(image_path,
                   cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_RGB2HSV),
                   criterion, lambda extracted: extracted > 0, "Yellow patches")


class ImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        file_name = os.path.basename(event.src_path)
        if file_name.startswith(PREFIX) and file_name.lower().endswith(
                ('.png', '.jpg', '.jpeg', '.tif')):
            p = event.src_path
            detect_brightness_total(p)


# Set up file monitoring
# event_handler = ImageHandler()
# observer = Observer()
# observer.schedule(event_handler, WATCH_DIR, recursive=False)
# observer.start()
#
# print(f"Monitoring directory: {WATCH_DIR} for new images...")

if __name__ == "__main__":
    functions = [detect_brightness_total, detect_hue_max, detect_yellow_num,
                 detect_patch_of_yellow]


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


    agitated_count = failed_count(False, '/agitated')
    base_count = failed_count(True, '/base')
    print(f"Failed count: {agitated_count}")
    print(f"Failed count: {base_count}")
    # try:
    #     while True:
    #         time.sleep(1)
    # except KeyboardInterrupt:
    #     observer.stop()
    # observer.join()
