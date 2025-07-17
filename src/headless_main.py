import os
import time
import glob
import cv2
from src import analyzer, sms_sender

# Get image directory from env var or fallback
IMAGE_DIR = os.environ.get("IMAGE_DIR", "/app/shared-images")

# create necessary objects
analyzer_obj = analyzer.Analyzer()
sms = sms_sender.SmsSender()
observer = analyzer.ObserverWrapper(analyzer_obj, sms, image_dir=IMAGE_DIR)

# check which files have already been processed
processed_files = set()

def run_headless():
    print(f"[HEADLESS] Starting headless analysis in {IMAGE_DIR}")
    
    # Start the signal detection observer 
    observer.start_monitoring()

    try:
        while True:
            # get all images in the directory
            image_files = sorted(
                glob.glob(os.path.join(IMAGE_DIR, "*.png")) +
                glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
            )

            # we need to  skip previously processed images
            for img_path in image_files:
                if img_path in processed_files:
                    continue
                if "_processed" in img_path:
                    continue  


                print(f"[HEADLESS] Processing new image: {img_path}")
                frame = cv2.imread(img_path)
                if frame is None:
                    print(f"[HEADLESS] Warning: couldn't read {img_path}")
                    continue

                # Perform analysis, draw bounding box + create logs
                analyzer_obj.paint_square(frame) 
                observer.event_handler.handle_image(frame)          
                
                # then save result
                base, ext = os.path.splitext(img_path)
                result_path = f"{base}_processed{ext}"
                cv2.imwrite(result_path, frame)
                print(f"[HEADLESS] Saved processed image as {result_path}")

                # done
                processed_files.add(img_path)

            time.sleep(1)  # pause before checking again

    # stopping process 
    except KeyboardInterrupt:
        print("[HEADLESS] Stopping...")
        observer.stop()
