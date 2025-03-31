import cv2
import numpy as np
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Parameters
WATCH_DIR = "./CROPPS_Training_Dataset"  # Change to your image directory
THRESHOLD = 1e7  # Adjust based on image intensity range
PREFIX = ""

def detect_brightness_total(image_path, threshold=THRESHOLD):
    image = cv2.imread(image_path)
    hsv_img = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    
    if image is None:
        print(f"Error loading {image_path}")
        return False, None

    total_intensity = np.sum(image)
    hue = np.min(abs(hsv_img[:, :, 0]-30))
    is_bright = total_intensity > threshold
    is_yellow = hue < 100

    print(f"Processed: {image_path}")
    print(f"Hue diff: {hue}")
    print(f"Agitated: {is_yellow}")
    print(f"Total Intensity: {total_intensity}")
    print(f"Brightness exceeds threshold: {is_bright}\n")

    return is_yellow, hue

class ImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_name = os.path.basename(event.src_path)
        if file_name.startswith(PREFIX) and file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tif')):
            detect_brightness_total(event.src_path)

# Set up file monitoring
event_handler = ImageHandler()
observer = Observer()
observer.schedule(event_handler, WATCH_DIR, recursive=False)
observer.start()

print(f"Monitoring directory: {WATCH_DIR} for new images...")

if __name__ == "__main__":
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
