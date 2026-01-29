import json
import os
import threading
import tkinter as tk

from src.app import DATA_PATH
from src.tools.triggers import *


class Trigger:
    def __init__(self, pre_trigger_func):
        self.pre_trigger_func = pre_trigger_func
        self.analysis_duration = 120  # seconds
        self._timer = None

    def pre_trigger(self):
        try:
            self.pre_trigger_func()
        except:
            print("[ERROR] Pre-trigger failed")

    def execute_trigger(self, new_msg):
        match new_msg:
            case "current injection" | '1':
                if not hasattr(self, "injection_duration") or not hasattr(self,
                                                                          "injection_amplitude"):
                    raise ValueError("Parameters not set")
                    # TODO: or possibly set default values here

                self.injection(self.current_injection_port,
                               self.injection_duration,
                               self.injection_amplitude)

            case "burn" | '2':
                if not hasattr(self, "burn_duration"):
                    raise ValueError("Burn duration not set")
                    # TODO: or possibly set a default value here

                self.burn("COM" + str(self.burn_port_com),
                          self.burn_duration)
            # TODO: more cases here

    def show_settings(self, dialog, exec_func, winfo_x, winfo_y, winfo_width,
                      winfo_height):
        def apply_trigger():
            for name, entry in all_entries:
                name = name.replace(' ', '_').replace(':', '').lower()
                value = entry.get().strip()
                if value:
                    setattr(self, name, value)
                    print(f"[INFO] Attribute \"{name}\" set to {value}")
            dialog.destroy()

        dialog.title("Set Serial Ports")
        dialog.geometry("320x500")
        dialog.resizable(False, False)

        # TODO: scrollbar is not bound to the whole window

        canvas = tk.Canvas(dialog)
        scrollbar = tk.Scrollbar(dialog, orient="vertical",
                                 command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Create a frame inside the canvas to contain the message
        content_frame = tk.Frame(canvas)
        canvas.create_window((10, 10), window=content_frame, anchor="nw")

        # ---- Create entries ----
        with open(str(DATA_PATH / "trigger_func.json")) as f:
            s = json.load(f)

        all_entries = []
        for key, setting in s.items():
            tk.Label(content_frame, text=setting["title"]).pack()

            for i in setting["items"]:
                frame = tk.Frame(content_frame)
                entry = tk.Entry(frame, width=25)
                entry.pack(side="right", padx=2)
                entry.bind("<Return>", lambda _: apply_trigger())
                frame.pack(fill="x", pady=5)
                tk.Label(frame, text=i).pack(side="right")
                all_entries.append((i, entry))

            for name, msg in setting["buttons"].items():
                frame = tk.Frame(content_frame)
                frame.pack(fill="x", pady=5)
                tk.Button(frame, text=name,
                          command=lambda msg=msg: [apply_trigger(),
                                                   exec_func(msg)],
                          width=10).pack()

        # ---- Error Label ----
        error_label = tk.Label(content_frame, text="", fg="red")
        error_label.pack()

        # ---- Buttons ----
        button_frame = tk.Frame(content_frame)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Apply", command=apply_trigger,
                  width=10).pack(side="left", padx=5)

        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                  width=10).pack(
            side="left", padx=5
        )

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Update the scrollable region of the canvas
        content_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        # ---- Center the dialog ----
        dialog.update_idletasks()
        x = winfo_x + (winfo_width // 2) - (
                dialog.winfo_width() // 2)
        y = winfo_y + (winfo_height // 2) - (
                dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        ### TRIGGER FUNCTIONS ###

    def injection(self, port, *args):
        self.pre_trigger()
        # Run injection in a separate thread to avoid blocking CaptureTask
        threading.Thread(target=injection.main, args=(port, *args),
                         daemon=True).start()

    def burn(self, port, *args):
        self.pre_trigger()
        # Run burn in a separate thread to avoid blocking CaptureTask
        threading.Thread(target=burn.main, args=(port, *args),
                         daemon=True).start()

    # TODO: add more
