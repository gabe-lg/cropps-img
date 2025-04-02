import heapq
from collections import deque

import cv2
import matplotlib
import numpy as np
import time
import os
import platform

from matplotlib import pyplot as plt
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

### PARAMETERS ###
# Change to your image directory (normalize slashes for platform!)
WATCH_DIR = ".\\CROPPS_Training_Dataset" if platform.system() == "Windows" \
    else "./CROPPS_Training_Dataset"
PREFIX = ""
SHOW_IMG = False
FAILED = 0

# TOTAL INTENSITY
THRESHOLD_TOTAL_INTENSITY = 21000000

# BRIGHT PIXELS
THRESHOLD_BRIGHT = 40
THRESHOLD_NUM_BRIGHT = 7000

# BRIGHT PATCHES
AREA_H = 10

AREA_V = 10
THRESHOLD_PATCHES = 99
READ_DELAY = 1

# NORMALIZED INTENSITY
THRESHOLD_NORMALIZED = 5
THRESHOLD_NORMALIZED_TOTAL = 50000

# LONGEST PATH
THRESHOLD_PATH = 0


### END OF PARAMETERS ###


# draw #
def paint_pixel(frame, x, y, color):
    assert isinstance(x, int) and isinstance(y, int)
    assert 0 <= x < frame.shape[0] and 0 <= y < frame.shape[1]
    assert isinstance(color, tuple) and len(color) == 3
    assert (0 <= color[i] <= 255 for i in range(3))

    frame[x, y] = color


def paint_square(frame, threshold_value=THRESHOLD_BRIGHT):
    """
    Function to draw a square around the region with the most white pixels in the given frame.

    :param frame: The current frame from the video stream.
    :param threshold_value: The threshold value to identify white pixels.
    :return: Frame with a square drawn around the white region.
    """
    # Convert the frame to grayscale
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply a binary threshold to isolate the white pixels
    _, thresholded = cv2.threshold(gray_frame, threshold_value, 255,
                                   cv2.THRESH_BINARY)

    # Find contours (white regions) in the thresholded image
    contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    # Find the largest contour (i.e., the region with the most white pixels)
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)

        # Get the bounding box of the largest contour
        x, y, w, h = cv2.boundingRect(largest_contour)

        # Draw a square (bounding box) around the largest region
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0),
                      2)  # Green square with thickness 2
    return frame


def paint_area(frame, threshold_value):
    pixels = frame.max(axis=2) > THRESHOLD_BRIGHT
    print(frame)
    frame[pixels] = [255, 0, 0]


def paint_path(frame, path, color, thickness):
    """
    Draws a thick line along a given path of pixel coordinates.

    :param frame: OpenCV frame (image)
    :param path: List of (x, y) tuples representing the path
    :param color: BGR color tuple (default: red)
    :param thickness: Line thickness
    """

    if len(path) < 2:
        return frame  # No line to draw

        # Convert (x, y) coordinates to NumPy array
    path_array = np.array(path, dtype=np.int32)

    # Draw a polyline connecting all points
    cv2.polylines(frame, [path_array], isClosed=False, color=color,
                  thickness=thickness)

    return frame


def longest_path(img):
    binary_mask = (img > (np.max(img) * 0.9)).astype(np.uint8)
    height, width = binary_mask.shape
    directions = [(i, j) for j in range(-1, 2) for i in range(-1, 2)]
    directions.remove((0, 0))

    x_start, y_start = cv2.minMaxLoc(binary_mask)[3]
    pq = []
    heapq.heappush(pq, (
        -binary_mask[x_start, y_start], (x_start, y_start), [(x_start,
                                                              y_start)]))

    # Visited set to prevent revisits
    visited = set()

    brightest_path = []

    while pq:
        neg_intensity, (x, y), path = heapq.heappop(
            pq)  # Get highest-intensity pixel

        if (x, y) in visited:
            continue
        visited.add((x, y))

        # Store the best path found
        if len(path) > len(brightest_path):
            brightest_path = path

        # Explore neighbors
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < height and 0 <= ny < width and (nx, ny) not in visited:
                heapq.heappush(pq, (
                    float(-binary_mask[nx, ny]), (nx, ny), path + [(nx,
                                                                    ny)]))

    return brightest_path


def plot_histogram(img):
    """
    Displays a histogram of pixel intensities for a given image.

    :param image_path: Path to the image file
    """
    matplotlib.use('TkAgg')
    # Compute histogram (256 bins for intensity values 0-255)
    hist = cv2.calcHist([img], [0], None, [256], [0, 256])

    # Plot histogram
    plt.figure(figsize=(8, 5))
    plt.plot(hist, color='black')
    plt.title("Pixel Intensity Histogram")
    plt.xlabel("Intensity Value")
    plt.ylabel("Pixel Count")
    plt.xlim([0, 256])
    plt.grid()
    plt.show()


def _detect(image_path, mask, extracted, criteria, desc) -> (bool, int):
    time.sleep(READ_DELAY)
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(image_path)
    img3 = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
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
    if SHOW_IMG and agitated:
        paint_square(img2)
        # paint_path(img2, longest_path(img), (255, 0, 0), 30)
        cv2.imshow("sample", img2)
        cv2.waitKey(0)
        cv2.destroyWindow("sample")
        plot_histogram(img3)
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


def normalize_brightness(image_path):
    def criteria(img):
        avg = int(np.average(img))
        img -= int(avg)
        return cv2.countNonZero(cv2.inRange(img, np.array(
            [int(avg * (1 + THRESHOLD_NORMALIZED / 100))]), np.array([
            100])))

    return _detect(image_path, None, criteria,
                   lambda extracted: extracted > THRESHOLD_NORMALIZED_TOTAL,
                   "Normalized intensity")


def combin(image_path):
    return (detect_yellow_num(image_path)[0] and normalize_brightness(
        image_path)[0], None)


functions = [combin]


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
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            print("stopped observer")


if __name__ == "__main__":
    WATCH_DIR = "../CROPPS_Training_Dataset"
    READ_DELAY = 0
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


    agitated_count = failed_count(False, '/agitated')
    base_count = failed_count(True, '/base')
    print(f"Failed count: {agitated_count}")
    print(f"Failed count: {base_count}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer_obj.stop()
