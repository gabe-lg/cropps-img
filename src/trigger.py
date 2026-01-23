import sys
from pathlib import Path
import threading

if __name__ == "__main__" or __package__ is None:
    _project_root = str(Path(__file__).resolve().parents[1])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

import assets.burn
import assets.injection

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

    def injection(self, port, *args):
        self.pre_trigger()
        # Run injection in a separate thread to avoid blocking CaptureTask
        threading.Thread(target=assets.injection.main, args=(port, *args), daemon=True).start()

    def burn(self, port, *args):
        self.pre_trigger()
        # Run burn in a separate thread to avoid blocking CaptureTask
        threading.Thread(target=assets.burn.main, args=(port, *args), daemon=True).start()

    # TODO: add more

if __name__ == '__main__':
    print("Please consider running main.py")
