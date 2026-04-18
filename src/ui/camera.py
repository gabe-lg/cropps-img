import threading
import time
import tkinter as tk
import tkinter.messagebox

from pathlib import Path

import numpy as np
from PIL import Image

from dlls.thorlabs_tsi_sdk.tl_camera import TLCameraSDK
from src.tools.image_queue import ImageAcquisitionThread

_ROOT_PATH = Path(__file__).resolve().parents[2]

SAVE_FREQ = 1
TARGET_FPS = 2.0  # frames per second (0.5 s gap between frames)
DEFAULT_EXPOSURE_MS = 1  # must be < (1000 / TARGET_FPS) - readout (~20 ms)
DEFAULT_GAIN = 20


class Camera:
    def __init__(self, setup_ok_event: threading.Event):
        self.setup_ok_event = setup_ok_event
        self.setup_failed_event = threading.Event()
        self.err = ""

        self.pil_image = None
        self.recording = False

    def setup(self):
        try:
            self.sdk = TLCameraSDK()
            camera_list = self.sdk.discover_available_cameras()
            self.camera = self.sdk.open_camera(camera_list[0])
        except Exception as e:
            if hasattr(self, 'sdk'):
                self.sdk.dispose()
            self.err = e
            self.setup_failed_event.set()
            return

        print("[CAMERA] Camera detected")
        print(f"[CAMERA] Sensor bit depth: {self.camera.bit_depth}-bit")

        self.image_acquisition_thread = ImageAcquisitionThread(self.camera,
                                                               SAVE_FREQ)
        print("[CAMERA] Setting parameters...")

        # Set exposure and gain defaults (user can change via settings dialog)
        try:
            self.camera.exposure_time_us = DEFAULT_EXPOSURE_MS * 1000
        except Exception as e:
            print(f"[CAMERA] Could not set exposure: {e}")
        try:
            self.camera.gain = DEFAULT_GAIN
        except Exception as e:
            print(f"[CAMERA] Could not set gain: {e}")

        # Enable hardware frame rate control for exact fps (must be set before arm)
        try:
            self.camera.frame_rate_control_value = TARGET_FPS
            self.camera.is_frame_rate_control_enabled = True
            print(f"[CAMERA] Frame rate locked at {TARGET_FPS} fps")
        except Exception as e:
            print(f"[CAMERA] Frame rate control unavailable: {e}")

        self.camera.frames_per_trigger_zero_for_unlimited = 0
        self.camera.arm(2)
        self.camera.issue_software_trigger()

        print("[CAMERA] Starting image acquisition thread...")
        self.image_acquisition_thread.start()

        self.setup_ok_event.set()
        print("[CAMERA] Setup done!")

    def latest_image(self):
        """
        Get the latest image from the camera, scaled for 8-bit display.
        The queued image is a 16-bit PIL Image carrying raw sensor data
        (e.g. 10-bit values 0-1023). We scale up to fill 16-bit range, then
        PIL's standard I;16 -> L conversion yields a correctly-contrasted
        8-bit image for Tkinter. Saved TIFFs remain untouched.
        """
        try:
            self.pil_image = \
                self.image_acquisition_thread.get_output_queue().queue[-1]
        except IndexError:
            # queue is empty
            pass

        if not self.pil_image:
            raise IndexError("No latest image")

        arr = np.asarray(self.pil_image, dtype=np.uint16)
        shift = max(0, 16 - self.camera.bit_depth)
        scaled = np.clip(arr.astype(np.uint32) << shift, 0, 65535).astype(np.uint16)
        return Image.fromarray(scaled, mode="I;16").convert("L")

    def show_settings_dialog(self, dialog, winfo_x, winfo_y, winfo_width,
                             winfo_height):
        def apply_exposure():
            try:
                exposure_ms = int(exposure_entry.get())
                max_ms = int(1000 / TARGET_FPS) - 20  # 20 ms readout margin
                if exposure_ms > max_ms:
                    tkinter.messagebox.showwarning(
                        "Exposure",
                        f"Exposure {exposure_ms}ms exceeds max for {TARGET_FPS} fps "
                        f"({max_ms}ms). Clamping to {max_ms}ms.")
                    exposure_ms = max_ms
                self.camera.exposure_time_us = exposure_ms * 1000

                tkinter.messagebox.showinfo(
                    "Exposure",
                    f"Exposure set to {round(self.camera.exposure_time_us / 1000, 2)}ms"
                )
            except Exception as e:
                tkinter.messagebox.showerror("Exposure", e)
            finally:
                dialog.destroy()

        def apply_gain():
            try:
                self.camera.gain = int(gain_entry.get())

                (
                    tkinter.messagebox.showinfo(
                        "Gain",
                        "Gain set to "
                        f"{round(self.camera.gain)}"
                    )
                )
            except Exception as e:
                tkinter.messagebox.showerror("Gain", e)
            finally:
                dialog.destroy()

        dialog.title("Exposure Settings")
        dialog.geometry("400x300")
        dialog.resizable(False, False)

        content_frame = tk.Frame(dialog)
        content_frame.pack(expand=True, fill="both", padx=20, pady=20)

        current_label = tk.Label(
            content_frame,
            text=f"Current exposure: {self.camera.exposure_time_us / 1000}ms"
        )
        current_label.pack(pady=(0, 10))

        input_frame = tk.Frame(content_frame)
        input_frame.pack(fill="x", pady=5)

        tk.Label(input_frame, text="New exposure:").pack(side="left")
        exposure_entry = tk.Entry(input_frame, width=25)
        exposure_entry.pack(side="left", padx=10)
        tk.Label(input_frame, text="milliseconds").pack(side="left", padx=2)

        button_frame = tk.Frame(content_frame)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Apply", command=apply_exposure, width=10).pack(
            side="left", padx=5
        )
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                  width=10).pack(
            side="left", padx=5
        )

        #-----------------------

        current_label = tk.Label(
            content_frame,
            text=f"Current gain: {self.camera.gain}"
        )
        current_label.pack(pady=(0, 10))

        input_frame = tk.Frame(content_frame)
        input_frame.pack(fill="x", pady=5)

        tk.Label(input_frame, text="New gain:").pack(side="left")
        gain_entry = tk.Entry(input_frame, width=45)
        gain_entry.pack(side="left", padx=10)

        button_frame = tk.Frame(content_frame)
        button_frame.pack()

        tk.Button(button_frame, text="Apply", command=apply_gain, width=10).pack(
            side="left", padx=5
        )
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                  width=10).pack(
            side="left", padx=5
        )

        gain_entry.bind("<Return>", lambda e: apply_gain())

        # Center the dialog on the main window
        dialog.update_idletasks()
        x = winfo_x + (winfo_width // 2) - (dialog.winfo_width() // 2)
        y = winfo_y + (winfo_height // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def start_stop_recording(self, button):
        """Start or stop recording video."""
        if self.recording:
            if button: button.config(text="Start recording")
            self.image_acquisition_thread.start_stop_recording(False)
            self.recording = False

            print("Video recording stopped.")
            return None

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        folder_path = _ROOT_PATH / "saves" / f"recordings_{timestamp}"
        folder_path.mkdir(parents=True)

        if button: button.config(text="Stop recording")
        self.image_acquisition_thread.image_dir = folder_path
        self.image_acquisition_thread.start_stop_recording(True)
        self.recording = True

        print(f"Video recording started. Folder: {folder_path}")
        return folder_path
