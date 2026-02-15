import csv
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import requests
import threading
import time
import tkinter as tk
from requests.auth import HTTPBasicAuth
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import Button, TextBox

class LoggernetLive:
    def __init__(self, csv_filename, interval=0.01):
        self.INTERVAL = interval
        self.MAX_DATA = int(120 / self.INTERVAL)
        self.USERNAME = "your_username"
        self.PASSWORD = "your_password"
        self.URL = 'http://192.168.66.1/cr6'
        self.PARAMS = {
            'command': 'DataQuery',
            'uri': 'dl:Data_Table',
            'mode': 'most-recent',
            'p1': 1,
            'format': 'json'
        }

        self.csv_filename = csv_filename
        self.timestamps = []
        self.data_list = []
        self.flag_list = []
        self.labels = None
        self.colors = None
        self.graph = []

        self.data_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.recording = False
        self.event_pending = False
        self.last_time_seen = None

        self.x_points_to_show = self.MAX_DATA
        self.y_min = None
        self.y_max = None
        self.auto_y_scale = True

        self.fig = plt.figure(figsize=(12, 8))
        self.ax = plt.subplot2grid((1, 4), (0, 0), colspan=3)

        self.setup_controls()

        threading.Thread(target=self.fetch_latest, daemon=True).start()
    def setup_controls(self):
        """Setup all control widgets on the right side"""
        
        # Recording control button
        ax_rec = plt.axes([0.77, 0.8, 0.2, 0.08])
        self.btn_rec = Button(ax_rec, 'Start Recording', color='lightgreen')
        self.btn_rec.on_clicked(self.toggle_recording)
        
        # Wounding event button
        ax_wound = plt.axes([0.77, 0.68, 0.2, 0.08])
        self.btn_wound = Button(ax_wound, 'Wounding Event', color='salmon')
        self.btn_wound.on_clicked(self.on_wound)
        
        # X-axis controls
        # Label for X-axis section
        self.fig.text(0.77, 0.58, 'X-Axis Control:', fontsize=10, fontweight='bold')
        
        # X points to show input
        self.fig.text(0.77, 0.54, 'Points to show:', fontsize=9)
        ax_x_points = plt.axes([0.77, 0.50, 0.15, 0.04])
        self.txt_x_points = TextBox(ax_x_points, '', initial=str(self.x_points_to_show))
        self.txt_x_points.on_submit(self.update_x_points)
        
        # X minutes to show input (alternative)
        self.fig.text(0.77, 0.46, 'Minutes to show:', fontsize=9)
        ax_x_minutes = plt.axes([0.77, 0.42, 0.15, 0.04])
        initial_minutes = self.x_points_to_show * self.INTERVAL / 60
        self.txt_x_minutes = TextBox(ax_x_minutes, '', initial=f'{initial_minutes:.2f}')
        self.txt_x_minutes.on_submit(self.update_x_minutes)
        
        # Y-axis controls
        # Label for Y-axis section
        self.fig.text(0.77, 0.35, 'Y-Axis Control:', fontsize=10, fontweight='bold')
        
        # Auto scale button
        ax_auto_y = plt.axes([0.77, 0.30, 0.2, 0.04])
        self.btn_auto_y = Button(ax_auto_y, 'Auto Y-Scale: ON', color='lightblue')
        self.btn_auto_y.on_clicked(self.toggle_auto_y)
        
        # Y min input
        self.fig.text(0.77, 0.26, 'Y Min:', fontsize=9)
        ax_y_min = plt.axes([0.77, 0.22, 0.15, 0.04])
        self.txt_y_min = TextBox(ax_y_min, '', initial='')
        self.txt_y_min.on_submit(self.update_y_min)
        
        # Y max input
        self.fig.text(0.77, 0.18, 'Y Max:', fontsize=9)
        ax_y_max = plt.axes([0.77, 0.14, 0.15, 0.04])
        self.txt_y_max = TextBox(ax_y_max, '', initial='')
        self.txt_y_max.on_submit(self.update_y_max)
        
        # Instructions
        self.fig.text(0.77, 0.08, 'Instructions:', fontsize=9, fontweight='bold')
        self.fig.text(0.77, 0.05, '• Enter values and press Enter', fontsize=8)
        self.fig.text(0.77, 0.02, '• Use Auto Y-Scale for dynamic range', fontsize=8)

    def update_x_points(self, text):
        """Update number of points to show on X-axis"""
        try:
            points = int(float(text))
            if points > 0:
                self.x_points_to_show = min(points, self.MAX_DATA)
                # Update the minutes box accordingly
                minutes = self.x_points_to_show * self.INTERVAL / 60
                self.txt_x_minutes.set_val(f'{minutes:.2f}')
                print(f"X-axis updated to show {self.x_points_to_show} points")
        except ValueError:
            print("Invalid input for X points")

    def update_x_minutes(self, text):
        """Update number of minutes to show on X-axis"""
        try:
            minutes = float(text)
            if minutes > 0:
                points = int(minutes * 60 / self.INTERVAL)
                self.x_points_to_show = min(points, self.MAX_DATA)
                # Update the points box accordingly
                self.txt_x_points.set_val(str(self.x_points_to_show))
                print(f"X-axis updated to show {minutes:.2f} minutes ({self.x_points_to_show} points)")
        except ValueError:
            print("Invalid input for X minutes")

    def toggle_auto_y(self, event):
        """Toggle automatic Y-axis scaling"""
        self.auto_y_scale = not self.auto_y_scale
        self.btn_auto_y.label.set_text(f'Auto Y-Scale: {"ON" if self.auto_y_scale else "OFF"}')
        self.btn_auto_y.color = 'lightblue' if self.auto_y_scale else 'lightgray'
        
        if not self.auto_y_scale:
            # If turning off auto scale, try to use current manual values
            self.apply_y_limits()
        
        print(f"Auto Y-scale: {'ON' if self.auto_y_scale else 'OFF'}")

    def update_y_min(self, text):
        """Update Y-axis minimum"""
        try:
            if text.strip():
                self.y_min = float(text)
                if not self.auto_y_scale:
                    self.apply_y_limits()
                print(f"Y minimum set to {self.y_min}")
            else:
                self.y_min = None
        except ValueError:
            print("Invalid input for Y min")

    def update_y_max(self, text):
        """Update Y-axis maximum"""
        try:
            if text.strip():
                self.y_max = float(text)
                if not self.auto_y_scale:
                    self.apply_y_limits()
                print(f"Y maximum set to {self.y_max}")
            else:
                self.y_max = None
        except ValueError:
            print("Invalid input for Y max")

    def apply_y_limits(self):
        """Apply manual Y-axis limits"""
        if self.y_min is not None and self.y_max is not None:
            self.ax.set_ylim(self.y_min, self.y_max)
        elif self.y_min is not None:
            current_ylim = self.ax.get_ylim()
            self.ax.set_ylim(self.y_min, current_ylim[1])
        elif self.y_max is not None:
            current_ylim = self.ax.get_ylim()
            self.ax.set_ylim(current_ylim[0], self.y_max)

    def fetch_latest(self):
        first_pass = True
        while not self.stop_event.is_set():
            try:
                resp = requests.get(self.URL, params=self.PARAMS, 
                                 auth=HTTPBasicAuth(self.USERNAME, self.PASSWORD), timeout=2)
                data = resp.json()
                fields = [f["name"] for f in data["head"]["fields"]]
                record = data["data"][0]
                t = record["time"]
                d = record["vals"]
                
                with self.data_lock:
                    if first_pass:
                        self.labels = fields
                        color_list = ["red", "blue", "green", "black", "orange", "purple", "cyan"]
                        self.colors = (color_list * ((len(self.labels) // len(color_list)) + 1))[:len(self.labels)]
                        self.graph = [self.ax.plot([], [], '-', label=lbl, color=clr)[0] 
                                    for lbl, clr in zip(self.labels[:-1], self.colors[:-1])]
                        
                        # Write CSV header
                        with open(self.csv_filename, 'w', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow(['Time'] + self.labels + ["Flag"])
                        first_pass = False
                    
                    # Only store new records (based on timestamp)
                    if t != self.last_time_seen:
                        self.timestamps.append(t)
                        self.data_list.append(d)
                        
                        # Event flag: Set to 1 if event is pending, else 0
                        if self.event_pending:
                            self.flag_list.append(1)
                            self.event_pending = False
                        else:
                            self.flag_list.append(0)
                        
                        self.timestamps[:] = self.timestamps[-self.MAX_DATA:]
                        self.data_list[:] = self.data_list[-self.MAX_DATA:]
                        self.flag_list[:] = self.flag_list[-self.MAX_DATA:]
                        
                        # Store ALL data to CSV only if recording is active
                        if self.recording:
                            with open(self.csv_filename, 'a', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow([t] + d + [self.flag_list[-1]])
                        
                        self.last_time_seen = t  # update after storing
                
                time.sleep(self.INTERVAL)
            except Exception as e:
                print("Error fetching data:", e)
                time.sleep(1)
        
        self.stop_event.set()

    def update(self, _):
        if self.stop_event.is_set():
            plt.close('all')
            return []
        
        with self.data_lock:
            if not self.data_list:
                return self.graph
            
            # Use only the specified number of points for display
            display_data = self.data_list[-self.x_points_to_show:]
            
            y_data = [list(col) for col in zip(*[row[:-1] for row in display_data])]
            x = np.arange(len(display_data))
            
            for i, line in enumerate(self.graph):
                if i < len(y_data):
                    line.set_data(x, y_data[i])
            
            # Set X-axis limits based on displayed data
            if len(display_data) > 0:
                self.ax.set_xlim(0, len(display_data))
            
            # Handle Y-axis scaling
            if self.auto_y_scale:
                self.ax.relim()
                self.ax.autoscale_view(scaley=True, scalex=False)
            else:
                self.apply_y_limits()
            
            title = "Live Logger Data — " + ("RECORDING" if self.recording else "paused")
            self.ax.set_title(title)
            self.ax.set_xlabel("Time (points, {:.2f}s steps)".format(self.INTERVAL))
            self.ax.set_ylabel("Surface_Potential [mV]")
            self.ax.legend(loc='upper left')
            self.ax.grid(True)
            
            # Update button label for start/stop
            self.btn_rec.label.set_text("Stop Recording" if self.recording else "Start Recording")
            self.btn_rec.color = "red" if self.recording else "lightgreen"
            
            return self.graph

    def toggle_recording(self, event):
        """Toggle recording state"""
        self.recording = not self.recording
        print("Recording started." if self.recording else "Recording stopped.")

    def on_wound(self, event):
        """Mark wounding event"""
        with self.data_lock:
            self.event_pending = True
        print("Wounding event flagged.")

    def run(self):
        # REMOVE plt.show(); instead open a dedicated Tk window
        root = tk.Tk()
        root.withdraw()  # hide the root window

        win = tk.Toplevel(root)
        win.title("Loggernet Live")

        canvas = FigureCanvasTkAgg(self.fig, master=win)
        canvas.get_tk_widget().pack(fill="both", expand=True)

        # If user closes the window, stop the thread and exit cleanly
        def on_close():
            self.stop_event.set()
            try:
                win.destroy()
            finally:
                root.quit()

        win.protocol("WM_DELETE_WINDOW", on_close)

        # IMPORTANT: keep references alive
        self.canvas = canvas
        self.ani = animation.FuncAnimation(
            self.fig,
            self.update,
            interval=int(self.INTERVAL * 1000),
            cache_frame_data=False
        )

        canvas.draw()
        root.mainloop()

if __name__ == '__main__':
    filename = input("Enter output CSV filename: ")
    # Change interval here (e.g., 0.01, 0.05, or 0.1 for 10, 20, or 100 Hz polling)
    LoggernetLive(filename, interval=0.01).run()