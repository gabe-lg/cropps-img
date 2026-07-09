"""One-step build for the CROPPS Demo executable.

Usage:  python build_exe.py

Runs PyInstaller against cropps-demo.spec, then copies the editable runtime
data folders (assets/, platform-tools/) next to the built .exe, skipping the
large runtime-output files that don't belong in a distributable.

Result:  dist/CROPPS-Demo/CROPPS-Demo.exe  (double-click to run)
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "CROPPS-Demo"

# Runtime-generated / irrelevant paths that must NOT be shipped.
ASSET_SKIP_DIRS = {"captured_data", "__pycache__", "CROPPS_Training_Dataset"}
# platform-tools files to ship (adb + its DLLs only; skip the keithley_*.csv logs).
PLATFORM_TOOLS_KEEP = {"adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll"}


def run_pyinstaller():
    print("[build] Running PyInstaller...")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "cropps-demo.spec"],
        cwd=ROOT, check=True,
    )


def copy_assets():
    dest = DIST / "assets"
    print(f"[build] Copying assets -> {dest}")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for item in (ROOT / "assets").iterdir():
        if item.name in ASSET_SKIP_DIRS:
            continue
        if item.is_dir():
            shutil.copytree(item, dest / item.name)
        else:
            shutil.copy2(item, dest / item.name)
    # Ensure the writable output folder exists (kept empty in the distributable).
    (dest / "captured_data").mkdir(exist_ok=True)


def copy_platform_tools():
    dest = DIST / "platform-tools"
    print(f"[build] Copying platform-tools -> {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    src = ROOT / "platform-tools"
    for name in PLATFORM_TOOLS_KEEP:
        f = src / name
        if f.exists():
            shutil.copy2(f, dest / name)
        else:
            print(f"[build][WARN] missing platform-tools/{name}")


def make_output_dirs():
    (DIST / "shared-images").mkdir(exist_ok=True)
    (DIST / "saves").mkdir(exist_ok=True)


def main():
    run_pyinstaller()
    copy_assets()
    copy_platform_tools()
    make_output_dirs()
    exe = DIST / "CROPPS-Demo.exe"
    print("\n[build] Done.")
    print(f"[build] Executable: {exe}")
    print("[build] Double-click that .exe to run the demo.")


if __name__ == "__main__":
    main()
