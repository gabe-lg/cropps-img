import os
import time
import glob
from src import analyzer, sms_sender

# Get image directory from env var or fallback
IMAGE_DIR = os.environ.get("IMAGE_DIR", "/app/shared-images")

# create necessary objects
analyzer_obj = analyzer.Analyzer()
sms = sms_sender.SmsSender()
observer = analyzer.ObserverWrapper(analyzer_obj, sms, image_dir=IMAGE_DIR)

# keep track of what's been processed already
processed_files = set()

def run_headless():
    print(f"[HEADLESS] Starting headless analysis in {IMAGE_DIR}")
    
    # Start the watchdog observer for real-time folder changes
    observer.start_monitoring()

    try:
        while True:
            # get all image files (jpg/png)
            image_files = sorted(
                glob.glob(os.path.join(IMAGE_DIR, "*.png")) +
                glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
            )

            for img_path in image_files:
                # Skip already processed
                if img_path in processed_files:
                    continue
                if "_processed" in img_path:
                    continue  # Don't analyze already processed images

                print(f"[HEADLESS] Processing new image: {img_path}")

                # Use analyzer directly – handles saving and DB logging
                analyzer_obj.combin(img_path, sms)

                # Track it as done
                processed_files.add(img_path)

            time.sleep(1)

    except KeyboardInterrupt:
        print("[HEADLESS] Stopping...")
        observer.stop()
