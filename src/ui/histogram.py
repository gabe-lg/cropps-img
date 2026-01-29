import cv2
import numpy as np
from matplotlib import pyplot as plt


class Histogram:
    def __init__(self):
        import numpy as np
        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.hist_line, = self.ax.plot(np.full(256, 255), color='black')
        self.ax.set_title("Pixel Intensity Histogram")
        self.ax.set_xlim(0.0, 256.0)
        self.ax.set_ylim(1, 1e6)
        self.ax.set_yscale('log')
        self.ax.set_xlabel("Intensity Value")
        self.ax.set_ylabel("Pixel Count")
        self.ax.grid(True)

    def update(self, img):
        # Compute histogram (256 bins for intensity values 0-255)
        hist = cv2.calcHist([np.array(img)], [0], None, [256], [0, 256]).flatten()
        self.hist_line.set_ydata(hist)
