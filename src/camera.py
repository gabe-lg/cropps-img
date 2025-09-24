import time
from pathlib import Path

import cv2
from instrumental import instrument, list_instruments

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 1024


class Camera:
    def __init__(self):
        self.app_fps = 2
        self.camera = instrument('uc480')
        self.camera.pixelclock = "5MHz"
        self.gain = 99
        self.camera.start_live_video(framerate="2Hz", exposure_time="500ms", \
                                    gain=self.gain)
        self.recording = False

    # destructor
    def __del__(self):
        try:
            self.camera.stop_live_video()
            self.camera.close()
        except Exception:
            pass  # Ignore errors during interpreter shutdown

    def get_frame(self):
        frame = self.camera.latest_frame(copy=True)
        return frame

    def is_recording(self):
        return self.recording

    def get_exposure(self):
        return self.camera.exposure

    def set_exposure(self, exposure_val: float):
        self.camera.exposure = exposure_val
        return

    def get_fps(self):
        return self.camera.framerate

    def set_fps(self, fps_val: float):
        self.camera.stop_live_video()
        self.camera.start_live_video(
                framerate=f"{float(fps_val)}Hz",
                exposure_time=self.camera.exposure,
                gain=self.gain)
        return

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
        fps_to_write = round(self.get_fps().magnitude)
        self.video_writer = cv2.VideoWriter(
            str(file_name), fourcc, fps_to_write,
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
