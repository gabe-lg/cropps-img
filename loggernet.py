import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import requests
import threading
import time
from requests.auth import HTTPBasicAuth

INTERVAL = 0.1  # time (in s) to wait before retrieving the next data point
MAX_DATA = 300  # max number of data points to show on graph
TITLE = "Title"
X_LABEL = "Time (s)"
Y_LABEL = "Value"

# in case we need authentication later on:
USERNAME = "your_username"
PASSWORD = "your_password"

timestamps = []  # x axis
data_list = []  # y axis
lines = []  # list of vertical lines


def fetch_latest():
    while 1:
        url = 'http://192.168.66.1/cr6'
        params = {
            'command': 'DataQuery',
            'uri': 'dl:Data_6June2025_gel',
            'mode': 'most-recent',
            'p1': 1,
            'format': 'json'
        }
        auth = HTTPBasicAuth(USERNAME, PASSWORD)

        try:
            data = requests.get(url, params=params, auth=auth).json()
            if "data" not in data:
                break
            record = data["data"][0]
            time_str = record["time"]
            temp = record["vals"]
            (t, d) = time_str, temp
        except Exception as e:
            print("Error fetching data:", e)
            break

        if not (t and d):
            break

        timestamps.append(t)
        data_list.append(d)
        data_list[:] = data_list[-MAX_DATA:]
        data_list[:] = [[np.nan if str(item).upper() == 'NAN' else item for item in row] for row in data_list]
        timestamps[:] = list(range(len(data_list) - 1, -1, -1))  # timestamps[-MAX_DATA:]
        lines[:] = [i + 1 for i in lines]
        print(timestamps)
        print(data_list)
        time.sleep(INTERVAL)


def update(frame):
    graph = []
    ax.clear()
    fig.canvas.mpl_connect('button_press_event', lambda _: lines.append(0))

    data_list_t = [[row[i] for row in data_list] for i in range(len(data_list[0]))]
    for l in data_list_t:
        graph.append(ax.plot(timestamps, l, marker='o')[0])  # get the Line2D artist
    for l in lines:
        if l < MAX_DATA:
            plt.axvline(x=l, color='red', linestyle='--', label='Plant wounded')

    ax.set_title(TITLE)
    ax.set_xlabel(X_LABEL)
    ax.set_ylabel(Y_LABEL)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.gca().invert_xaxis()

    return graph


if __name__ == '__main__':
    threading.Thread(target=fetch_latest).start()
    fig, ax = plt.subplots()
    ani = animation.FuncAnimation(fig, update, interval=INTERVAL, cache_frame_data=False)
    plt.show()
