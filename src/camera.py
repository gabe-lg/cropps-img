from instrumental import instrument, list_instruments
import cv2


class Camera:
    def __init__(self):
        self.camera = instrument('uc480')
        self.camera.start_live_video(framerate = "2Hz", exposure_time="50ms")
        self.camera.pixelclock = "5MHz"

    # destructor
    def __del__(self):
        self.camera.stop_live_video()
        self.camera.close()
    
    def get_frame(self):
        # frame = self.camera.grab_image(timeout='10s', copy=True, exposure_time='10ms')
        frame = self.camera.latest_frame(copy=True)
        frame = cv2.normalize(frame, None, 0, 255, cv2.NORM_MINMAX)
        return frame

if __name__ == "__main__":
    cam = Camera()