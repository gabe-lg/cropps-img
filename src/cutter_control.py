import socket
import tkinter as tk
from tkinter import messagebox

def cutter_app():
    # ---------- CONFIG ----------
    ARDUINO_IP = "192.168.4.1"  # Default Arduino AP IP
    PORT = 8080
    TIMEOUT = 3.0  # seconds

    # ---------- Socket Functions ----------
    def send_command(down_angle, up_angle, hold_time):
        try:
            # Create a TCP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            
            print(f"Attempting to connect to {ARDUINO_IP}:{PORT}...")
            sock.connect((ARDUINO_IP, PORT))
            print("Connected successfully!")
            
            # Prepare the command
            command = f"{down_angle},{up_angle},{hold_time}\n"
            print(f"Sending command: {command.strip()}")
            
            sock.sendall(command.encode())
            sock.close()
            return True
        except socket.timeout:
            print("Error: Connection timed out!")
            return False
        except ConnectionRefusedError:
            print("Error: Connection refused (is Arduino running?)")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

    # ---------- GUI Functions ----------
    def send_cut():
        try:
            down_angle = down_slider.get()
            up_angle = up_slider.get()
            hold_time = speed_slider.get()

            # Validate inputs
            if not (0 <= down_angle <= 180) or not (0 <= up_angle <= 180):
                raise ValueError("Angles must be between 0-180")

            if send_command(down_angle, up_angle, hold_time):
                status_label.config(text=f"Sent: {down_angle}, {up_angle}, {hold_time}ms", fg="green")
            else:
                status_label.config(text="Failed to send command!", fg="red")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            status_label.config(text=f"Error: {e}", fg="red")

    # ---------- GUI Setup ----------
    root = tk.Tk()
    root.title("🔥 Cutter Control Panel")
    root.geometry("400x450")
    root.config(bg="#1e1e1e")

    # Widgets
    title = tk.Label(root, text="Cutter Control Panel", font=("Arial", 20), fg="white", bg="#1e1e1e")
    title.pack(pady=10)

    # Down Angle Slider
    tk.Label(root, text="Down Angle (0-180)", font=("Arial", 12), fg="white", bg="#1e1e1e").pack()
    down_slider = tk.Scale(root, from_=0, to=180, orient="horizontal", length=300, bg="#1e1e1e", fg="white")
    down_slider.set(0)
    down_slider.pack(pady=5)

    # Up Angle Slider
    tk.Label(root, text="Up Angle (0-180)", font=("Arial", 12), fg="white", bg="#1e1e1e").pack()
    up_slider = tk.Scale(root, from_=0, to=180, orient="horizontal", length=300, bg="#1e1e1e", fg="white")
    up_slider.set(90)
    up_slider.pack(pady=5)

    # Hold Time Slider
    tk.Label(root, text="Hold Time (ms)", font=("Arial", 12), fg="white", bg="#1e1e1e").pack()
    speed_slider = tk.Scale(root, from_=100, to=2000, resolution=100, orient="horizontal", length=300, bg="#1e1e1e", fg="white")
    speed_slider.set(500)
    speed_slider.pack(pady=5)

    # CUT Button
    cut_button = tk.Button(root, text="CUT!", font=("Arial", 24, "bold"), command=send_cut, bg="#FF5555", fg="white", activebackground="#FF0000")
    cut_button.pack(pady=20)

    # Status Label
    status_label = tk.Label(root, text="Ready", font=("Arial", 12), fg="white", bg="#1e1e1e")
    status_label.pack(pady=10)

    root.mainloop()
