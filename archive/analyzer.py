import os
import time
from typing import Any, Callable, Optional, Union

import cv2
import numpy as np
from matplotlib import use, pyplot as plt
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import src.analysis.db
import src.tools.sms_sender


class Analyzer:
    def __init__(self):
        self.MAX_PROCESSED_IMAGES = 300

        # Change to your image directory (normalize slashes for platform!)
        self.dir = r"C:\Users\CROPPS-in-Box\Documents\cropps main folder\cropps-img\assets\captured_data"

        # the file cannot be read immediately after saving. Controls the number of
        # seconds to wait before the file is read
        self.read_delay = 0.1

        # only send a message if it is agitated twice in a row
        self.agitated_count = 0

        # the cooldown period: the number of cycles before another text message can
        # be sent to the user
        self.cooldown = 5
        self.cooldown_tmp = 0

        # A value of 0 hides any popups. A value of 1 shows both the analyzed image
        # and a histogram showing the intensities of every pixel
        self.show_img = 1

        self.is_test = 0

        # Failed count for testing
        self.failed = 0

        # Other than testing, only one function should be called.
        self.functions = [self.combin]

        ### Thresholds for analysis - see functions below for specifications ###
        # BRIGHT PIXELS
        self.threshold_bright = 60  # intensity ranges from 0 to 255
        self.threshold_num_bright = 4000  # 1228800 (1280 * 960) pixels in an
        # image

        # NORMALIZED INTENSITY
        self.threshold_normalized = 5
        self.threshold_normalized_total = 6000

    def testing_init(self):
        self.dir = "../assets/CROPPS_Training_Dataset"
        self.read_delay = 0
        self.is_test = 1

    def paint_square(self, frame: cv2.Mat | np.ndarray[Any, np.dtype]) \
            -> cv2.Mat | np.ndarray[Any, np.dtype]:
        """
        Function to draw a square around the region with the most white pixels in the given frame.

        :param frame: The current frame from the video stream.
        :return: Frame with a square drawn around the white region.
        """
        # Convert the frame to grayscale
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply a binary threshold to isolate the white pixels
        _, thresholded = cv2.threshold(gray_frame, self.threshold_bright, 255,
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

    @staticmethod
    def plot_histogram(img: cv2.Mat | np.ndarray[Any, np.dtype]) -> None:
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

    def _detect(self, image_path: str, extracted: Callable[
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
        time.sleep(self.read_delay)
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"[ANALYSIS] Error loading {image_path}")
            return False, None
        if self.show_img:
            self.plot_histogram(img)
        data = extracted(img)
        agitated = criterion(data)
        print(f"[ANALYSIS] {desc}: {data}")
        return agitated, data

    def detect_yellow_num(self, image_path: str) -> tuple[bool, int]:
        """
        Counts the total number of pixels with intensity greater than
        `THRESHOLD_BRIGHT`. The image is categorized as "agitated" if that number
        is greater than `THRESHOLD_NUM_BRIGHT`.
        """
        # TODO: THIS IS A REALLY BAD FUNCTION
        return self._detect(image_path,
                            lambda img: np.count_nonzero(
                                img > self.threshold_bright),
                            lambda
                                extracted: extracted > self.threshold_num_bright,
                            "Yellow pixels")

    def normalize_brightness(self, image_path: str) -> tuple[bool, int]:
        """
        Finds the average intensity of all the pixels in the image. Then,
         count the total number of pixels with intensity `THRESHOLD_NORMALIZED`
         percent greater than the average. The image is categorized as "agitated" if
         that number is greater than `THRESHOLD_NORMALIZED_TOTAL`.
        """

        # TODO: THIS IS A REALLY BAD FUNCTION
        def criteria(img):
            avg = int(np.average(img))
            img -= int(avg)
            return cv2.countNonZero(cv2.inRange(img, np.array(
                [int(avg * (1 + self.threshold_normalized / 100))]), np.array([
                100])))

        return self._detect(image_path, criteria, lambda
            extracted: extracted > self.threshold_normalized_total,
                            "Normalized intensity")

    def detect_sparse_bright_pixels(self, image_path: str) -> tuple[bool, int]:
        """
        Detects agitation by looking for sparse bright pixels.
        Returns True (agitated) when there are FEW bright pixels (between min and max thresholds).
        Returns False when there are too many or too few bright pixels.
        """

        # TODO: THIS IS A BETTER BUT STILL REALLY BAD FUNCTION
        def count_bright_pixels(img):
            # Count pixels above brightness threshold
            bright_pixels = np.count_nonzero(img > self.threshold_bright)
            return bright_pixels

        def is_agitated(count):
            # Define min and max thresholds for number of bright pixels
            MIN_BRIGHT_PIXELS = 1000  # Minimum number to consider valid
            MAX_BRIGHT_PIXELS = 500000  # Maximum number before considered too bright

            # Return True only if count is between min and max
            return MIN_BRIGHT_PIXELS <= count <= MAX_BRIGHT_PIXELS

        return self._detect(image_path, count_bright_pixels, is_agitated,
                            "Sparse bright pixels")

    def combin(self, image_path: str):
        processed_dir = os.path.join("/app/shared-images", "processed")
        os.makedirs(processed_dir, exist_ok=True)

        basename = os.path.basename(image_path)
        final_path = os.path.join(processed_dir, basename)

        try:
            # Run analysis
            a = self.detect_yellow_num(image_path)
            b = self.normalize_brightness(image_path)
            res = (a[0] and b[0], None)

            # Save processed image
            frame = cv2.imread(image_path)
            frame = self.paint_square(frame)
            cv2.imwrite(final_path, frame)

            # Trim old processed files
            processed_imgs = sorted(
                [f for f in os.listdir(processed_dir) if
                 f.lower().endswith((".png", ".jpg", ".jpeg"))],
                key=lambda x: os.path.getctime(os.path.join(processed_dir, x))
            )
            if len(processed_imgs) > self.MAX_PROCESSED_IMAGES:
                for old_file in processed_imgs[
                    :len(processed_imgs) - self.MAX_PROCESSED_IMAGES]:
                    os.remove(os.path.join(processed_dir, old_file))

            print(
                f"[DEBUG] Inserting to DB: yellow={a[1]}, normalized={b[1]}, agitated={res[0]}, path={final_path}")
            src.analysis.db.insert_data(
                yellow_pixels=a[1],
                normalized_pixels=b[1],
                agitation=res[0],
                image_path=final_path
            )

            print(f"[ANALYSIS] Agitated: {res[0]}\n")

        except Exception as e:
            print(f"[DB ERROR from analyzer] {e}")

        # Cooldown logic stays as is


class ImageHandler(FileSystemEventHandler):
    def __init__(self, analyzer: Analyzer,
                 sms_sender: src.tools.sms_sender.SmsSender):
        super().__init__()
        self.analyzer = analyzer
        self.sms_sender = sms_sender

    def on_created(self, event):
        if event.is_directory:
            return
        file_name = os.path.basename(event.src_path)
        if "_processed" in file_name.lower():
            return  # Skip processed images
        if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tif')):
            print(f"[HEADLESS] Processing new image: {event.src_path}")
            for func in self.analyzer.functions: func(event.src_path)
            self.analyzer.combin(event.src_path)


class ObserverWrapper:
    def __init__(self, analyzer: Analyzer,
                 sms_sender: src.tools.sms_sender.SmsSender,
                 image_dir=r"C:\Users\CROPPS-in-Box\Documents\cropps main folder\cropps-img\assets\captured_data"
                 ):
        self.event_handler = ImageHandler(analyzer, sms_sender)
        self.observer = Observer()
        self.analyzer = analyzer
        self.image_dir = image_dir

    def start_monitoring(self):
        print(f"Monitoring directory: {self.image_dir} for new images...")
        self.observer.schedule(self.event_handler, self.image_dir,
                               recursive=False)
        self.observer.start()

    def stop(self):
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            print("stopped observer")
