import threading
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk
ASSETS_PATH = Path(__file__).parent.parent / "assets"
BG_PATH = ASSETS_PATH / "cropps_background.png"


class LoadingScreen:
    def __init__(self, parent: tk.Tk):
        """
        :param parent: the parent widget where the loading UI is created
        """
        self.parent = parent
        self._running = True

        # Outer frame that you can pack/place/grid in the main app
        self.loading_frame = tk.Frame(parent, bg="white")
        self.loading_frame.place(relx=0.5, rely=0.5,
                         anchor="center")  # center on parent

        # Load and display background
        try:
            bg_image = Image.open(BG_PATH).resize((400, 300))
            self.bg_photo = ImageTk.PhotoImage(bg_image)
            tk.Label(self.loading_frame, image=self.bg_photo).pack()
        except Exception as e:
            print(f"Error loading background: {e}")
            self.loading_frame.configure(bg="white")

        # Create canvas for rotating circle
        self.loading_canvas = tk.Canvas(self.loading_frame, width=50, height=50)
        self.loading_canvas.pack(pady=(20, 5))  # Reduced bottom padding

        # Add loading text
        tk.Label(
            self.loading_frame, text="Loading...", font=("Comic Sans MS", 16)
        ).pack(pady=(0, 20))

        # Initialize loading animation
        self.angle = 60

        self._animate_loading()

    def __del__(self):
        self._running = False
        self.loading_frame.destroy()

    def _animate_loading(self):
        """Animate the loading circle"""
        self.loading_canvas.delete("all")

        # Draw rotating arc
        # TODO: Bad loading icon
        self.loading_canvas.create_arc(
            5, 5, 45, 45, start=self.angle, extent=300, fill="", outline="blue",
            width=2
        )

        self.angle = (self.angle - 10) % 360
        self.loading_canvas.after(50, self._animate_loading)
