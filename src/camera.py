import time
from pathlib import Path

import cv2
from instrumental import instrument, list_instruments

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 960
CAMERA_FPS = 2


class Camera:
    def __init__(self):
        self.camera = instrument('uc480')
        self.camera.auto_gain = True
        self.camera.start_live_video(framerate="2Hz", exposure_time="500ms")
        self.camera.pixelclock = "5MHz"
        self.recording = False

    # destructor
    def __del__(self):
        try:
            self.camera.stop_live_video()
            self.camera.close()
        except Exception:
            pass  # Ignore errors during interpreter shutdown

    def get_frame(self):
        # frame = self.camera.grab_image(timeout='10s', copy=True, exposure_time='10ms')
        frame = self.camera.latest_frame(copy=True)
        # Convert to grayscale if needed (CLAHE works on 1-channel images)
        # if len(frame.shape) == 3 and frame.shape[2] == 3:
        #     frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # else:
        #     frame_gray = frame

        # # Adaptive gain using CLAHE
        # clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        # frame_eq = clahe.apply(frame_gray)

        return frame

    def is_recording(self):
        return self.recording

    def get_fps(self):
        return CAMERA_FPS

    def start_recording(self):
        if self.is_recording():
            print("[WARNING] Camera already recording!")
            return

        self.recording = True
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        file_name = Path(
            __file__).parent.parent / "saves" / f"video_{timestamp}.avi"
        file_name.parent.mkdir(parents=True, exist_ok=True)

        fourcc = cv2.VideoWriter.fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(
            str(file_name), fourcc, CAMERA_FPS,
            (CAMERA_WIDTH, CAMERA_HEIGHT))
        return file_name

    def write_video_frame(self):
        if self.video_writer:
            frame = self.get_frame()
            frame_3ch = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            frame_3ch = cv2.resize(frame_3ch, (CAMERA_WIDTH, CAMERA_HEIGHT))
            self.video_writer.write(frame_3ch)

    def stop_recording(self):
        self.recording = False
        self.video_writer.release()


if __name__ == "__main__":
    print("[WARNING] Running camera module directly. Consider running main.py.")
    cam = Camera()
