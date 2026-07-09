import os
import sys
from pathlib import Path

# Run from the app's base directory so relative paths (./assets/...) resolve
# correctly regardless of where the user launches from. When frozen into an
# .exe this is the folder containing the executable; otherwise it's this
# script's own folder.
if getattr(sys, "frozen", False):
    _base = Path(sys.executable).resolve().parent
else:
    _base = Path(__file__).resolve().parent
os.chdir(_base)

# if the environment variable HEADLESS is 1, we run headless mode
if os.environ.get("HEADLESS") == "1":
    from src.headless_main import run_headless

    run_headless()

# otherwise we run GUI based mode
else:
    from src import app

    app.main()
