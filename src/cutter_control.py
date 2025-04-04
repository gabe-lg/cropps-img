import socket
import tkinter as tk
import time


def cutter_app():
    # ---------- CONFIG ----------
    ARDUINO_IP = "192.168.4.1"
    PORT = 8080
    TIMEOUT = 1.0  # seconds

    # ---------- Socket Sender ----------
    def send_command(cmd):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(TIMEOUT)
                sock.connect((ARDUINO_IP, PORT))
                time.sleep(0.05)  # <<< allows Arduino time to prep
                sock.sendall((cmd + '\n').encode())
            status_label.config(text=f"Sent: {cmd}", fg="green")
        except Exception as e:
            print(f"Error: {e}")
            status_label.config(text=f"Error: {e}", fg="red")

    # ---------- Jog Control ----------
    def on_press(cmd):
        send_command(cmd)

    def on_release(cmd):
        send_command(cmd)

    # ---------- Servo ----------
    def send_cut():
        down = down_slider.get()
        up = up_slider.get()
        hold = speed_slider.get()
        send_command(f"SERVO,{down},{up},{hold}")

    # ---------- GUI ----------
    root = tk.Tk()
    root.title("🔥 ControlHub GUI (WiFi)")
    root.geometry("400x600")
    root.config(bg="#1e1e1e")

    tk.Label(root, text="Control Panel", font=("Arial", 20), fg="white",
             bg="#1e1e1e").pack(pady=10)

    # ---------- D-Pad ----------
    pad_frame = tk.Frame(root, bg="#1e1e1e")
    pad_frame.pack(pady=10)

    btn_up = tk.Button(pad_frame, text="↑", width=10, height=2)
    btn_up.grid(row=0, column=1, padx=5, pady=5)
    btn_up.bind('<ButtonPress>', lambda e: on_press('w'))
    btn_up.bind('<ButtonRelease>', lambda e: on_release('x'))

    btn_left = tk.Button(pad_frame, text="←", width=10, height=2)
    btn_left.grid(row=1, column=0, padx=5, pady=5)
    btn_left.bind('<ButtonPress>', lambda e: on_press('a'))
    btn_left.bind('<ButtonRelease>', lambda e: on_release('z'))

    btn_right = tk.Button(pad_frame, text="→", width=10, height=2)
    btn_right.grid(row=1, column=2, padx=5, pady=5)
    btn_right.bind('<ButtonPress>', lambda e: on_press('d'))
    btn_right.bind('<ButtonRelease>', lambda e: on_release('z'))

    btn_down = tk.Button(pad_frame, text="↓", width=10, height=2)
    btn_down.grid(row=2, column=1, padx=5, pady=5)
    btn_down.bind('<ButtonPress>', lambda e: on_press('s'))
    btn_down.bind('<ButtonRelease>', lambda e: on_release('x'))

    # ---------- Servo Controls ----------
    tk.Label(root, text="Servo Down Angle", font=("Arial", 12), fg="white",
             bg="#1e1e1e").pack()
    down_slider = tk.Scale(root, from_=0, to=180, orient="horizontal",
                           length=300, bg="#1e1e1e", fg="white")
    down_slider.set(30)
    down_slider.pack(pady=5)

    tk.Label(root, text="Servo Up Angle", font=("Arial", 12), fg="white",
             bg="#1e1e1e").pack()
    up_slider = tk.Scale(root, from_=0, to=180, orient="horizontal", length=300,
                         bg="#1e1e1e", fg="white")
    up_slider.set(90)
    up_slider.pack(pady=5)

    tk.Label(root, text="Hold Time (ms)", font=("Arial", 12), fg="white",
             bg="#1e1e1e").pack()
    speed_slider = tk.Scale(root, from_=100, to=2000, resolution=100,
                            orient="horizontal", length=300, bg="#1e1e1e",
                            fg="white")
    speed_slider.set(500)
    speed_slider.pack(pady=5)

    tk.Button(root, text="✂️ Execute Cut", command=send_cut, bg="#FF5555",
              fg="white").pack(pady=10)

    # ---------- Status ----------
    status_label = tk.Label(root, text="Ready", font=("Arial", 12), fg="white",
                            bg="#1e1e1e")
    status_label.pack(pady=10)

    root.mainloop()
