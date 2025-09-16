import cv2
import os
import time
import numpy as np

RAW_DIR = "./shared-images"
PROCESSED_DIR = os.path.join(RAW_DIR, "processed")
REFRESH_INTERVAL = 2  # seconds
DISPLAY_HEIGHT = 350  # try 300–400 for comfort

def get_latest_image(folder):
    images = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
    if not images:
        return None
    images.sort(key=lambda x: os.path.getctime(os.path.join(folder, x)))
    return images[-1]

def resize_image(img, height=DISPLAY_HEIGHT):
    if img is None:
        return None
    scale = height / img.shape[0]
    width = int(img.shape[1] * scale)
    return cv2.resize(img, (width, height))

def main():
    print("[DEMO] Viewer started. Press ESC to quit.")
    last_seen = ""

    while True:
        latest_raw = get_latest_image(RAW_DIR)
        if latest_raw and latest_raw != last_seen:
            last_seen = latest_raw
            raw_path = os.path.join(RAW_DIR, latest_raw)
            processed_path = os.path.join(PROCESSED_DIR, latest_raw)

            img_raw = cv2.imread(raw_path)

            # Wait for processed image to appear (up to 2 seconds)
            max_wait = 20  # 20 x 0.1s = 2s
            wait_count = 0
            img_proc = None
            while wait_count < max_wait:
                img_proc = cv2.imread(processed_path)
                if img_proc is not None:
                    break
                time.sleep(0.1)
                wait_count += 1

            if img_raw is None:
                print(f"[WARNING] Could not read: {raw_path}")
                continue

            if img_proc is None:
                print(f"[WARNING] Processed image NOT found after wait: {processed_path}")
                img_proc = 255 * np.ones_like(img_raw)  # white placeholder

            img_raw_resized = resize_image(img_raw)
            img_proc_resized = resize_image(img_proc)

            combined = cv2.hconcat([img_raw_resized, img_proc_resized])
            cv2.imshow("CROPPS DEMO (Raw | Processed)", combined)
            print(f"[DEMO] Showing: {latest_raw}")

        key = cv2.waitKey(REFRESH_INTERVAL * 1000)
        if key == 27:  # ESC key
            print("[DEMO] Exiting viewer.")
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()