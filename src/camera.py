import threading

from dlls.thorlabs_tsi_sdk.tl_camera import TLCameraSDK
from lib.image_queue import ImageAcquisitionThread

SAVE_FREQ = 3


class Camera:
    def __init__(self, event: threading.Event):
        self.event = event

        try:
            self.sdk = TLCameraSDK()
            camera_list = self.sdk.discover_available_cameras()
            self.camera = self.sdk.open_camera(camera_list[0])
        except Exception as e:
            self.camera = None
            # raise RuntimeError(f"[CAMERA] Error loading camera: {e}")

        print("[CAMERA] Camera detected")

    def setup(self):
        self.image_acquisition_thread = ImageAcquisitionThread(self.camera,
                                                               SAVE_FREQ)
        print("[CAMERA] Setting parameters...")
        self.camera.frames_per_trigger_zero_for_unlimited = 0
        self.camera.arm(2)
        self.camera.issue_software_trigger()

        print("[CAMERA] Starting image acquisition thread...")
        self.image_acquisition_thread.start()

        self.event.set()
        print("[CAMERA] Setup done!")
