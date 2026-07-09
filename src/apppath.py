"""Resolve the application's base directory.

When running as a normal Python script this is the project root (the folder
that contains ``assets/``, ``platform-tools/``, ``main.py``).

When running as a PyInstaller-built executable ``__file__`` points *inside*
the frozen bundle, which is read-only and not where the user's editable
``assets/``/``platform-tools/`` folders live.  In that case the base dir is
the folder that contains the ``.exe`` instead, so all data files and writable
output folders (``saves/``, ``shared-images/``, ``assets/captured_data/``)
resolve to plain folders sitting next to the executable.
"""

import sys
from pathlib import Path


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
