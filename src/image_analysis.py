import os
import threading
import tkinter as tk
import tkinter.messagebox

import cv2
import matplotlib.pyplot as plt
import numpy as np

from src.capture_task import CaptureTask
from src.remote_image_analysis import remote_image_analysis

# Image dimensions
IMAGE_WIDTH = 1440
IMAGE_HEIGHT = 1080

# Pixel intensity range to track
MIN_INTENSITY = 20
MAX_INTENSITY = 170

# Analysis parameters
MAX_FRAMES = 101  # Check first 100 frames for detection
THRESHOLD_NOTHING = 35  # Pixels <50: Nothing happened
THRESHOLD_INJECTION = 10000  # Pixels 50-10000: Current injection

# Flag to enable/disable figure creation
CREATE_FIGURE = True


def start_analysis(camera, directory, button, command):
    directory.mkdir(parents=True, exist_ok=True)
    capture_task = CaptureTask(camera, directory)
    capture_task.start()

    if button:
        button.config(text="Stop Analysis", fg="darkred",
                      command=command)

    return capture_task


def stop_analysis(sms_sender, directory, button, command):
    if button:
        button.config(
            text="Start Analysis", fg="darkgreen",
            command=command)

    # variable to control remote/local analysis
    REMOTE = False

    # Show a non-blocking "waiting" message
    waiting_win = tk.Toplevel()
    waiting_win.title("Please wait")
    tk.Label(
        waiting_win,
        text=f"Running {"remote" if REMOTE else "local"} analysis...\nThis may take a while.",
    ).pack(padx=30, pady=30)

    def worker():
        try:
            if REMOTE:
                result = remote_image_analysis(directory)
            else:
                print(directory)
                result = image_analysis(directory)

            try:
                sms_sender.send_msg_after_analysis(result)
            except RuntimeError:
                waiting_win.after(0, lambda: tkinter.messagebox.showinfo(
                    "Analysis Result", f"Detection result: {result}"))
        except Exception as e:
            waiting_win.after(0, lambda e=e: tkinter.messagebox.showerror(
                "Analysis Error", f"Failed to analyze images: {e}"))
        finally:
            waiting_win.after(0, waiting_win.destroy)

    threading.Thread(target=worker).start()


def plot_pixel_counts_vs_prev(pixel_counts_prev, screenshot_directory):
    """Plot pixel counts (intensity 40-170 after previous frame subtraction) vs. frame number and save."""
    frame_numbers = [i for i in range(2, len(pixel_counts_prev) + 2)]

    plt.figure(figsize=(10, 6))  # TODO: cannot be called in another thread
    plt.plot(frame_numbers, pixel_counts_prev, marker='o', linestyle='-',
             color='b')
    plt.xlabel('Frame Number')
    plt.ylabel('Pixel Count (Intensity 40-170)')
    plt.title('Pixel Count (40-170) vs. Frame Number - Previous Frame')
    plt.grid(True)
    plt.savefig(os.path.join(screenshot_directory,
                             'pixel_count_40_170_vs_prev_plot.png'))
    plt.close()


def plot_pixel_counts_vs_background(pixel_counts_bg, screenshot_directory):
    """Plot pixel counts (intensity 40-170 after background frame subtraction) vs. frame number and save."""
    frame_numbers = [i for i in range(2, len(pixel_counts_bg) + 2)]

    plt.figure(figsize=(10, 6))
    plt.plot(frame_numbers, pixel_counts_bg, marker='o', linestyle='-',
             color='r')
    plt.xlabel('Frame Number')
    plt.ylabel('Pixel Count (Intensity 40-170)')
    plt.title('Pixel Count (40-170) vs. Frame Number - Background Frame')
    plt.grid(True)
    plt.savefig(
        os.path.join(screenshot_directory, 'pixel_count_40_170_vs_bg_plot.png'))
    plt.close()


def detect_conditions(pixel_counts_prev):
    """Detect conditions based on pixel counts (40-170, frame vs. previous) in the first 30 frames."""
    if not pixel_counts_prev:
        return "No frames for detection"

    frames_to_check = pixel_counts_prev[
        :min(MAX_FRAMES - 1, len(pixel_counts_prev))]
    result = "Nothing happened"

    for count in frames_to_check:
        if count > THRESHOLD_INJECTION:
            return "Burn"
        elif THRESHOLD_NOTHING <= count <= THRESHOLD_INJECTION:
            result = "Current injection"

    return result


def image_analysis(screenshot_directory):
    """
    Analyze images in the specified directory:
    - Compute pixel counts (40-170) for frame vs. previous and frame vs. background.
    - Generate separate plots for both.
    - Return detection result based on frame vs. previous differences.
    """
    all_files = [f for f in os.listdir(screenshot_directory) if
                 f.endswith('.tiff')]

    if not all_files:
        return "No images found"

    all_files.sort(key=lambda x: int(x.split('.')[0]))

    if len(all_files) < 2:
        return "Insufficient images"

    pixel_counts_vs_prev = []
    pixel_counts_vs_bg = []
    background_image = None
    prev_image = None

    for i, image_file in enumerate(all_files, start=1):
        image_path = os.path.join(screenshot_directory, image_file)
        current_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if current_image is None or current_image.shape != (IMAGE_HEIGHT,
                                                            IMAGE_WIDTH):
            continue

        if i == 1:
            background_image = current_image
            prev_image = current_image
            continue

        if prev_image is not None:
            difference_prev = cv2.subtract(current_image, prev_image)
            count_vs_prev = np.sum((difference_prev >= MIN_INTENSITY) & (
                    difference_prev <= MAX_INTENSITY))
            pixel_counts_vs_prev.append(count_vs_prev)

        if background_image is not None:
            difference_bg = cv2.subtract(current_image, background_image)
            count_vs_bg = np.sum((difference_bg >= MIN_INTENSITY) & (
                    difference_bg <= MAX_INTENSITY))
            pixel_counts_vs_bg.append(count_vs_bg)

        prev_image = current_image

    # Save pixel count data
    output_file_prev = os.path.join(screenshot_directory,
                                    'pixel_counts_vs_prev.txt')
    with open(output_file_prev, 'w') as f:
        f.write("Frame Number,Pixel Count (40-170 vs Previous Frame)\n")
        for i, count in enumerate(pixel_counts_vs_prev, start=2):
            f.write(f"{i},{count}\n")

    output_file_bg = os.path.join(screenshot_directory,
                                  'pixel_counts_vs_bg.txt')
    with open(output_file_bg, 'w') as f:
        f.write("Frame Number,Pixel Count (40-170 vs Background)\n")
        for i, count in enumerate(pixel_counts_vs_bg, start=2):
            f.write(f"{i},{count}\n")

    # Generate plots
    if CREATE_FIGURE:
        if pixel_counts_vs_prev:
            plot_pixel_counts_vs_prev(pixel_counts_vs_prev,
                                      screenshot_directory)
        if pixel_counts_vs_bg:
            plot_pixel_counts_vs_background(pixel_counts_vs_bg,
                                            screenshot_directory)

    return detect_conditions(pixel_counts_vs_prev)
