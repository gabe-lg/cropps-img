import csv
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import requests
import threading
import time
from requests.auth import HTTPBasicAuth


class Loggernet:
    def __init__(self):
        self.INTERVAL = 0.1  # time (in s) to wait before retrieving the next data point
        self.MAX_DATA = 30  # max number of data points to show on graph
        self.TITLE = "Title"
        self.X_LABEL = "Time (s)"
        self.Y_LABEL = "Value"

        # Authentication credentials
        self.USERNAME = "your_username"
        self.PASSWORD = "your_password"

        # Data storage
        self.timestamps = []  # x axis
        self.data_list = []  # y axis
        self.labels = ["SE1", "SE2", "voltage diff"]
        self.colors = ["red", "blue", "black"]
        self.lines = []  # list of vertical lines

        # Threading and plotting setup
        self.data_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.fig, self.ax = plt.subplots()
        self.graph = [self.ax.plot(self.timestamps, self.data_list, '-',
                                   label=self.labels[i], color=self.colors[i])[0]
                      for i in range(3)]

        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('key_press_event', self.on_click)
        self.fig.canvas.mpl_connect('close_event', self.on_close)

        threading.Thread(target=self.fetch_latest, daemon=True).start()
        self.init()

    def fetch_latest(self):
        with open('./assets/data.csv', 'w', newline='') as file:
            csv.writer(file).writerows([[self.X_LABEL] + self.labels])

        while not self.stop_event.is_set():
            url = 'http://192.168.66.1/cr6'
            params = {
                'command': 'DataQuery',
                'uri': 'dl:Data_6June2025_gel',
                'mode': 'most-recent',
                'p1': 1,
                'format': 'json'
            }
            auth = HTTPBasicAuth(self.USERNAME, self.PASSWORD)

            try:
                data = requests.get(url, params=params, auth=auth).json()
                if "data" not in data:
                    break
                record = data["data"][0]
                time_str = record["time"]
                vals = record["vals"]
                (t, d) = time_str, vals
            except Exception as e:
                print("Error fetching data:", e)
                break

            if not (t and d):
                break

            with self.data_lock:
                self.data_list.append(d)
                self.data_list[:] = self.data_list[-self.MAX_DATA:]
                self.data_list[:] = [[np.nan if str(item).upper() == 'NAN' else item
                                      for item in row] for row in self.data_list]
                self.timestamps[:] = list(range(len(self.data_list) - 1, -1, -1))
                self.lines[:] = [i + 1 for i in self.lines]

            with open('./assets/data.csv', 'a', newline='') as file:
                csv.writer(file).writerows([[t] + d[:3]])
                if self.lines and self.lines[-1] == 1:
                    csv.writer(file).writerows([["--- Plant wounded ---"]])
            time.sleep(self.INTERVAL)
        print("Data fetching stopped.")
        self.stop_event.set()

    def init(self):
        self.ax.set_title(self.TITLE)
        self.ax.set_xlabel(self.X_LABEL)
        self.ax.set_ylabel(self.Y_LABEL)
        self.ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plt.xticks(rotation=45)
        plt.gca().invert_xaxis()
        return self.graph

    def update(self, _):
        if self.stop_event.is_set():
            print("Closing plot.")
            plt.close('all')
            return []

        with self.data_lock:
            x = list(self.timestamps)
            y_data = [list(col) for col in zip(*self.data_list)] if self.data_list else [[] for _ in self.labels]
            vlines = list(self.lines)

        for i, line in enumerate(self.graph):
            if i < len(y_data):
                line.set_data(x, y_data[i])

        [l.remove() for l in self.ax.lines[len(self.graph):]]

        latest_line = min(vlines) if vlines else -1
        for i in vlines:
            if i < self.MAX_DATA:
                self.ax.axvline(x=i, color='red', linestyle='--',
                                label='Plant wounded' if i == latest_line else None)

        plt.tight_layout()
        self.ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        self.ax.relim()
        self.ax.autoscale_view()
        return self.graph

    def on_click(self, _):
        with self.data_lock:
            self.lines.append(0)

    def on_close(self, _):
        self.stop_event.set()
        plt.close('all')

    def run(self):
        ani = animation.FuncAnimation(self.fig, self.update, init_func=self.init,
                                      interval=self.INTERVAL, cache_frame_data=False)
        plt.show()
        print("Program exiting.")


if __name__ == '__main__':
    Loggernet().run()
