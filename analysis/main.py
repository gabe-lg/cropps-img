import cv2
import numpy as np
import os
import platform
import send_sms
import time

from matplotlib import use, pyplot as plt
from typing import Any, Callable, Optional, Union
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

### GLOBAL VARIABLES ###
# Change to your image directory (normalize slashes for platform!)
WATCH_DIR = ".\\captured_data" if platform.system() == "Windows" \
    else "./captured_data"

# the file cannot be read immediately after saving. Controls the number of
# seconds to wait before the file is read
READ_DELAY = 0.1

# the cooldown period: the number of cycles before another text message can
# be sent to the user
COOLDOWN = 5

# A value of 0 hides any popups. A value of 1 shows both the analyzed image
# and a histogram showing the intensities of every pixel
SHOW_IMG = 1

IS_TEST = 0

### Thresholds for analysis - see functions below for specifications ###
# BRIGHT PIXELS
THRESHOLD_BRIGHT = 40  # intensity ranges from 0 to 255
THRESHOLD_NUM_BRIGHT = 7000  # 1228800 (1280 * 960) pixels in an image

# NORMALIZED INTENSITY
THRESHOLD_NORMALIZED = 5
THRESHOLD_NORMALIZED_TOTAL = 50000

### END OF GLOBAL VARIABLES ###


cooldown_tmp = 0


def paint_square(frame: cv2.Mat | np.ndarray[Any, np.dtype],
                 threshold_value: int = THRESHOLD_BRIGHT) \
        -> cv2.Mat | np.ndarray[Any, np.dtype]:
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


def plot_histogram(img: str) -> None:
    """
    Displays a histogram of pixel intensities for a given image.

    :param img: Path to the image file
    """
    use('TkAgg')
    # Compute histogram (256 bins for intensity values 0-255)
    hist = cv2.calcHist([img], [0], None, [256], [0, 256])

    plt.figure(figsize=(8, 5))
    plt.plot(hist, color='black')
    plt.title("Pixel Intensity Histogram")
    plt.xlabel("Intensity Value")
    plt.ylabel("Pixel Count")
    plt.xlim([0, 256])
    plt.yscale('log')
    plt.grid()
    plt.show()


def _detect(image_path: str, extracted: Callable[
    [Union[cv2.Mat, np.ndarray[Any, np.dtype]]], int],
            criterion: Callable[[int], bool], desc: str) \
        -> tuple[bool, Optional[int]]:
    """
    Helper function that analyzes the image located in `image_path`
    Args:
        image_path: path of image
        extracted: function that takes in an image, analyzes it, and returns
         an `int`
        criterion: function that takes in an `int` and returns a `bool` based
         on certain criteria
        desc: description of the function

    Returns: the return values of `criterion` and `extracted`

    """
    time.sleep(READ_DELAY)
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(image_path)
    img3 = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"[ANALYSIS] Error loading {image_path}")
        return False, None
    data = extracted(img)
    agitated = criterion(data)
    print(f"[ANALYSIS] {desc}: {data}")
    if SHOW_IMG:
        plot_histogram(img3)
    return agitated, data


def detect_yellow_num(image_path: str) -> tuple[bool, int]:
    """
    Counts the total number of pixels with intensity greater than
    `THRESHOLD_BRIGHT`. The image is categorized as "agitated" if that number
    is greater than `THRESHOLD_NUM_BRIGHT`.
    """
    return _detect(image_path,
                   lambda img: np.count_nonzero(img > THRESHOLD_BRIGHT),
                   lambda extracted: extracted > THRESHOLD_NUM_BRIGHT,
                   "Yellow pixels")


def normalize_brightness(image_path: str) -> tuple[bool, int]:
    """
    Finds the average intensity of all the pixels in the image. Then,
     count the total number of pixels with intensity `THRESHOLD_NORMALIZED`
     percent greater than the average. The image is categorized as "agitated" if
     that number is greater than `THRESHOLD_NORMALIZED_TOTAL`.
    """

    def criteria(img):
        avg = int(np.average(img))
        img -= int(avg)
        return cv2.countNonZero(cv2.inRange(img, np.array(
            [int(avg * (1 + THRESHOLD_NORMALIZED / 100))]), np.array([
            100])))

    return _detect(image_path, criteria,
                   lambda extracted: extracted > THRESHOLD_NORMALIZED_TOTAL,
                   "Normalized intensity")


def combin(image_path: str) -> tuple[bool, Optional[int]]:
    """
    The image is categorized as "agitated" if and only if all the functions
    above categorizes it as "agitated".
    """
    global cooldown_tmp
    print(f"[ANALYSIS] Processed: {image_path}")
    a = detect_yellow_num(image_path)
    b = normalize_brightness(image_path)
    res = (a[0] and b[0], None)
    print(f"[ANALYSIS] Agitated: {res[0]}\n")
    if cooldown_tmp:
        cooldown_tmp -= 1
    elif res[0] and not IS_TEST:
        send_sms.main()
        cooldown_tmp = COOLDOWN
    print(f"Cooldown: {cooldown_tmp}")
    return res


# Other than testing, only one function should be called.
functions = [combin]


class ImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        file_name = os.path.basename(event.src_path)
        if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tif')):
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
    # Run this to test the analysis functions.
    WATCH_DIR = "../CROPPS_Training_Dataset"
    READ_DELAY = 0
    FAILED = 0
    IS_TEST = 1
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
