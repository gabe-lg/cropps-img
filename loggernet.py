import csv
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import os
import requests
import threading
import time
from requests.auth import HTTPBasicAuth

INTERVAL = 0.1  # time (in s) to wait before retrieving the next data point
MAX_DATA = 30  # max number of data points to show on graph
TITLE = "Title"
X_LABEL = "Time (s)"
Y_LABEL = "Value"

# in case we need authentication later on:
USERNAME = "your_username"
PASSWORD = "your_password"

timestamps = []  # x axis
data_list = []  # y axis
labels = ["SE1", "SE2", "voltage diff"]
colors = ["red", "blue", "black"]
lines = []  # list of vertical lines

fig, ax = plt.subplots()


def fetch_latest():
    with open('./assets/data.csv', 'w', newline='') as file:
        csv.writer(file).writerows([[X_LABEL] + labels])
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
            vals = record["vals"]
            (t, d) = time_str, vals
        except Exception as e:
            print("Error fetching data:", e)
            break

        if not (t and d):
            break

        data_list.append(d)
        data_list[:] = data_list[-MAX_DATA:]
        data_list[:] = [[np.nan if str(item).upper() == 'NAN' else item for item in row] for row in data_list]
        timestamps[:] = list(range(len(data_list) - 1, -1, -1))
        lines[:] = [i + 1 for i in lines]
        
        with open('./assets/data.csv', 'a', newline='') as file:
            csv.writer(file).writerows([[t] + d[:3]])
            if lines and lines[-1] == 1:
                csv.writer(file).writerows([["--- Plant wounded ---"]])
        time.sleep(INTERVAL)
    os._exit(0)


def update(frame):
    graph = []
    ax.clear()

    data_list_t = [([row[i] for row in data_list], labels[i], colors[i]) for i in range(3)]
    for i in data_list_t:
        graph.append(ax.plot(timestamps, i[0], marker='o', label=i[1], color=i[2])[0])  # get the Line2D artist
    for i in lines:
        if i < MAX_DATA:
            plt.axvline(x=i, color='red', linestyle='--', label='Plant wounded')

    ax.set_title(TITLE)
    ax.set_xlabel(X_LABEL)
    ax.set_ylabel(Y_LABEL)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.gca().invert_xaxis()

    return graph


def main():
    threading.Thread(target=fetch_latest, daemon=True).start()

    fig.canvas.mpl_connect('button_press_event', lambda _: lines.append(0))
    fig.canvas.mpl_connect('close_event', lambda _: os._exit(0))
    ani = animation.FuncAnimation(fig, update, interval=INTERVAL, cache_frame_data=False)
    plt.show()


if __name__ == '__main__':
    main()
