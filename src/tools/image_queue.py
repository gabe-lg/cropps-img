"""
Credits: Addapted from `Windows SDK and Doc. for Scientific Cameras by ThorLab
<https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ThorCam>`_
"""

import queue
import threading
import time
from pathlib import Path
from typing import Optional

from PIL import Image

from dlls.thorlabs_tsi_sdk.tl_camera import Frame
from dlls.thorlabs_tsi_sdk.tl_camera_enums import SENSOR_TYPE
from dlls.thorlabs_tsi_sdk.tl_mono_to_color_processor import \
    MonoToColorProcessorSDK


class ImageAcquisitionThread(threading.Thread):
    """
    This class derives from threading.Thread and is given a TLCamera instance during initialization. When started, the
    thread continuously acquires frames from the camera and converts them to PIL Image objects. These are placed in a
    queue.Queue object that can be retrieved using get_output_queue(). The thread doesn't do any arming or triggering,
    so users will still need to setup and control the camera from a different thread. Be sure to call stop() when it is
    time for the thread to stop.
    """

    def __init__(self, camera, save_freq=1):
        super(ImageAcquisitionThread, self).__init__()
        self._camera = camera
        self._previous_timestamp = 0
        self._image_dir = None
        self._image_count = 0
        self.save_freq = save_freq

        # setup color processing if necessary
        if self._camera.camera_sensor_type != SENSOR_TYPE.BAYER:
            # Sensor type is not compatible with the color processing library
            self._is_color = False
        else:
            self._mono_to_color_sdk = MonoToColorProcessorSDK()
            self._image_width = self._camera.image_width_pixels
            self._image_height = self._camera.image_height_pixels
            self._mono_to_color_processor = self._mono_to_color_sdk.create_mono_to_color_processor(
                SENSOR_TYPE.BAYER,
                self._camera.color_filter_array_phase,
                self._camera.get_color_correction_matrix(),
                self._camera.get_default_white_balance_matrix(),
                self._camera.bit_depth
            )
            self._is_color = True

        self._bit_depth = camera.bit_depth
        self._camera.image_poll_timeout_ms = 0  # Do not want to block for long periods of time
        self._image_queue = queue.Queue()
        self._queue_lock = threading.Lock()
        self._last_image_queue = None
        self._stop_event = threading.Event()

    @property
    def image_dir(self) -> Optional[Path]:
        """
        ``None`` if camera is not recording.
        Otherwise, the path of the folder to write to.
        """
        return self._image_dir

    @image_dir.setter
    def image_dir(self, recording: Optional[Path]):
        self._image_dir = recording

    def start_stop_recording(self, is_start):
        if self._last_image_queue:
            self._last_image_queue.shutdown()

        if is_start:
            # Just started recording
            self._last_image_queue = None
            self._image_queue.shutdown()
            with self._queue_lock:
                self._image_count = 0
        else:
            self._last_image_queue = self._image_queue
            threading.Thread(target=self.save_images, args=(True,)).start()

        self._image_queue = queue.Queue()

    def get_output_queue(self):
        return self._image_queue

    def save_images(self, force_save=False):
        with self._queue_lock:
            q = self._last_image_queue

        if not q: return
        self._last_image_queue = None

        with self._queue_lock:
            if self._image_dir or force_save:
                dir = self._image_dir

                while not q.empty():
                    img = q.get().convert("I;16")

                    if self._image_count % self.save_freq == 0:
                        img.save(f"{dir}\\{self._image_count}-{time.strftime("%Y%m%d_%H%M%S")}.tiff")

                    self._image_count += 1
                print(
                    f"Saved {self._image_count // self.save_freq} images in total to {dir}")

                if force_save: self.image_dir = None

        q.shutdown()

    def stop(self):
        self._stop_event.set()

    def _get_color_image(self, frame):
        # type: (Frame) -> Image
        # verify the image size
        width = frame.image_buffer.shape[1]
        height = frame.image_buffer.shape[0]
        if (width != self._image_width) or (height != self._image_height):
            self._image_width = width
            self._image_height = height
            print(
                "Image dimension change detected, image acquisition thread was updated")
        # color the image. transform_to_24 will scale to 8 bits per channel
        color_image_data = self._mono_to_color_processor.transform_to_24(
            frame.image_buffer,
            self._image_width,
            self._image_height)
        color_image_data = color_image_data.reshape(self._image_height,
                                                    self._image_width, 3)
        # return PIL Image object
        return Image.fromarray(color_image_data, mode='RGB')

    def _get_image(self, frame):
        # type: (Frame) -> Image
        # no coloring, just scale down image to 8 bpp and place into PIL Image object
        scaled_image = frame.image_buffer >> (self._bit_depth - 8)
        return Image.fromarray(scaled_image)

    def run(self):
        while not self._stop_event.is_set():
            try:
                frame = self._camera.get_pending_frame_or_null()
                if frame is not None:
                    if self._is_color:
                        pil_image = self._get_color_image(frame)
                    else:
                        pil_image = self._get_image(frame)
                    self._image_queue.put_nowait(pil_image)
            except queue.Full:
                # No point in keeping this image around when the queue is full, let's skip to the next one
                pass
            except Exception as error:
                print(
                    "Encountered error: {error}, image acquisition will stop.".format(
                        error=error))
                break
            finally:
                # keep at most 100 images
                if self._image_queue.qsize() > 99:
                    if self._last_image_queue:
                        print(f"Warning: last {self._last_image_queue.qsize()}"
                              " images are discarded.")
                        self._last_image_queue.shutdown()

                    # create new queue
                    self._last_image_queue = self._image_queue
                    self._image_queue = queue.Queue()
                    threading.Thread(target=self.save_images).start()

        print("Image acquisition has stopped")

        # images still in the queue are discarded
        self._image_queue.shutdown(immediate=True)

        if self._last_image_queue:
            self._last_image_queue.shutdown(immediate=True)

        if self._is_color:
            self._mono_to_color_processor.dispose()
            self._mono_to_color_sdk.dispose()
