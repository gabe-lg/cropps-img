import difflib
import json
import os
import queue
import re
import subprocess
import threading
import time
import tkinter as tk
import tkinter.messagebox

from pathlib import Path

# Resolve paths without importing src.app (avoids circular import)
_ROOT_PATH = Path(__file__).resolve().parents[2]
_DATA_PATH = _ROOT_PATH / "src" / "data"
_BG_PATH = _ROOT_PATH / "assets" / "cropps_background.png"


def fix_encoding(data):
    """
    Fix mis-decoded UTF-8 text that appears as Latin-1 (e.g., 'â€"' → '—', 'ðŸ"¥' → '🔥').
    """
    return re.sub(r'\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}',
                  lambda match: bytes(match.group(0), 'utf-8')
                  .decode('unicode_escape'), data)


class SmsSender:
    def __init__(self):
        # The path where adb was installed
        self.dir = str(_ROOT_PATH / "platform-tools")
        self.adb = os.path.join(self.dir, "adb")
        self.name = ""   # empty string so message.replace("$NAME", self.name) is safe
        self.phone = None
        self.phone_for_debug = ""  # change

        self.sms_msgs = ""  # full output
        self.new_msg_event = threading.Event()
        self.msg_changed_event = threading.Event()
        self.new_msgs = queue.Queue()  # individual msgs
        self.init_ms = int(time.time() * 1000)

        # messages to send
        with open(str(_DATA_PATH / "sms_template.json")) as f:
            self.template = json.load(f)

        if not os.path.isdir(self.dir):
            raise FileNotFoundError(
                f"ADB platform-tools directory not found: {self.dir}"
            )

        try:
            # Increase the SMS sending limit
            subprocess.run([
                self.adb, "shell", "settings", "put", "global",
                "sms_outgoing_check_max_count", "99999"
            ], cwd=self.dir, check=True)

            # Increase the SMS sending interval window (in milliseconds)
            subprocess.run([
                self.adb, "shell", "settings", "put", "global",
                "sms_outgoing_check_interval_ms", "9000000"
            ], cwd=self.dir, check=True)

            print("SMS sending limit increased.")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")

    def show_dialog(self, dialog):
        dialog.title("Enter SMS Details")
        dialog.config(bg="white")

        # create label and checkbox for receiving messages
        receive_sms_var = tk.BooleanVar()
        receive_sms_label = tk.Label(
            dialog,
            text="Would you like to receive text messages from a plant?",
            font=("TkTextFont", 18),
            bg="white",
        )
        receive_sms_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        receive_sms_checkbox = tk.Checkbutton(
            dialog, variable=receive_sms_var, bg="white"
        )
        receive_sms_checkbox.grid(row=0, column=2, padx=10, pady=10)

        # create label and input for the name
        name_label = tk.Label(
            dialog, text="Enter name: ", font=("TkTextFont", 18), bg="white"
        )
        name_label.grid(row=1, column=0, padx=10, pady=10)
        name_entry = tk.Entry(dialog)
        name_entry.grid(row=1, column=1, padx=10, pady=10)

        # create label and input for the phone number
        contact_label = tk.Label(
            dialog, text="Enter phone number: ", font=("TkTextFont", 18),
            bg="white"
        )
        contact_label.grid(row=2, column=0, padx=10, pady=10)
        contact_entry = tk.Entry(dialog)
        contact_entry.grid(row=2, column=1, padx=10, pady=10)

        # Label for displaying error messages
        error_label = tk.Label(
            dialog, text="", fg="red", font=("TkTextFont", 18), bg="white"
        )
        error_label.grid(row=3, column=0, columnspan=2, padx=12, pady=10)

        def send_info():
            name = name_entry.get()
            contact = contact_entry.get()

            # Only set contact info if the checkbox is checked
            if receive_sms_var.get():
                if not name or not contact:
                    error_label.config(
                        text="Please provide a name and phone number.")
                else:
                    self.set_info(name, contact)

                    try:
                        for i in range(len(
                                text := self.template
                                ["initial_text"]["current"])):
                            self.send_msg(text[i])
                    except RuntimeError as e:
                        tkinter.messagebox.showerror(
                            "Error", f"Could not send message: {e}")
                    finally:
                        dialog.destroy()
            else:
                error_label.config(
                    text="Please check the box and provide all details.")

        # Create Save button
        save_button = tk.Button(dialog, text="Save", command=send_info)
        save_button.grid(row=4, column=0, padx=10, pady=10)

        # Create Cancel button
        cancel_button = tk.Button(dialog, text="Cancel",
                                  command=dialog.destroy)
        cancel_button.grid(row=4, column=1, padx=10, pady=10)

        dialog.bind("<Return>", lambda _: send_info())
        dialog.bind("<Escape>", lambda _: dialog.destroy())

        image = tk.PhotoImage(file=_BG_PATH)
        image_label = tk.Label(dialog, image=image)
        image_label.grid(row=5, column=0, columnspan=2, padx=2, pady=10)
        image_label.image = image

        dialog.grab_set()

    def set_info(self, contact_name: str, contact_phone: str):
        """
        Sets `name` and `phone`.
        """
        self.name = contact_name
        self.phone = contact_phone

    def get_msg_history(self, phone: str):
        """
        Returns a list of messages (both sent and received) for the given phone
        number, starting from self.init_ms. Each message is represented as a dict:
        {
            "type": "sent" | "received",
            "body": <message text>,
            "timestamp": <epoch ms>
        }
        """

        # Read received (inbox) messages
        inbox_cmd = [
            self.adb, 'shell', 'content', 'query',
            '--uri', 'content://sms/inbox',
            '--projection', 'address,body,date',
            '--where', f"date\\>={self.init_ms}"
        ]
        inbox_output = subprocess.run(inbox_cmd, cwd=self.dir, check=True,
                                      capture_output=True).stdout.decode(
            "utf-8", errors="ignore")

        # Read sent messages
        sent_cmd = [
            self.adb, 'shell', 'content', 'query',
            '--uri', 'content://sms/sent',
            '--projection', 'address,body,date',
            '--where', f"date\\>={self.init_ms}"
        ]
        sent_output = subprocess.run(sent_cmd, cwd=self.dir, check=True,
                                     capture_output=True).stdout.decode(
            "utf-8", errors="ignore")

        def parse_sms_output(output: str, msg_type: str, phone: str):
            msgs = []
            if not output:
                return msgs

            # Split by "Row:" lines
            row_blocks = re.split(r"Row:\s*\d+\s*", output)
            for block in row_blocks:
                block = block.strip()
                if not block:
                    continue

                # Match fields using a more tolerant regex
                # Handles commas inside body and trailing whitespace
                match = re.search(
                    r"address=([^,]+),\s*body=(.*),\s*date=(\d+)", block,
                    re.DOTALL
                )
                if not match:
                    continue

                address, body, date = match.groups()
                if phone not in address:
                    continue

                body = body.strip()

                msgs.append({
                    "type": msg_type,
                    "body": body,
                    "timestamp": int(date)
                })

            return msgs

        inbox_msgs = parse_sms_output(inbox_output, "received", phone)
        sent_msgs = parse_sms_output(sent_output, "sent", phone)

        # Merge and sort chronologically
        all_msgs = inbox_msgs + sent_msgs
        all_msgs.sort(key=lambda m: m["timestamp"])

        return all_msgs

    def read_msg(self):
        """
        Continuously monitors text messages sent to the connected phone and
        prints a list of new messages received at every iteration.
        :param days_ago: Read messages received up to `days_ago` days ago.
        """
        # not_TODO: only read messages from the contact added in the box 
        # Handled by `get_msg_history`. This function is useful since it only
        #  execute one command per cycle. Also controls `new_msg_event`.

        while True:
            cmd = [
                self.adb, 'shell', 'content', 'query',
                '--uri', 'content://sms/inbox',
                '--where', f'date\\>={self.init_ms}',
                '--projection', 'body'
            ]

            try:
                output = subprocess.run(cmd, cwd=self.dir, check=True,
                                        capture_output=True, text=True).stdout
                orig = [r.partition("body=")[2].strip() for r in
                        self.sms_msgs.splitlines() if "body=" in r]
                new = [r.partition("body=")[2].strip() for r in
                       output.splitlines() if "body=" in r]

                diff = difflib.unified_diff(orig, new, fromfile='original',
                                            tofile='new', lineterm='')

                for line in diff:
                    if line.startswith('+') and not line.startswith('+++'):
                        self.new_msgs.put(line[1:].lower().strip())
                        self.new_msg_event.set()
                        self.msg_changed_event.set()

                self.sms_msgs = output
            except subprocess.CalledProcessError:
                pass
            finally:
                # 2 seconds ok?
                time.sleep(2)

    def send_debug_msg(self, message: str):
        self.send_msg(self.phone_for_debug, message)

    def send_msg(self, message, phone=None):
        if not phone: phone = self.phone
        if not phone: return

        message = fix_encoding(message).replace("$NAME", self.name)

        command = [
            self.adb,
            "shell",
            "am",
            "startservice",
            "--user", "0",
            "-n", "com.android.shellms/.sendSMS",
            "-e", "contact", phone,
            "-e", "msg", f"'{message}'"
        ]

        try:
            subprocess.run(command, cwd=self.dir, check=True)
            self.msg_changed_event.set()
            print("[send_msg]: A message has been sent.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(e)

    def send_msg_after_analysis(self, result):
        if not self.phone:
            raise RuntimeError("Phone number not set.")

        match result.lower().strip():
            case "current injection":
                self.send_msg(self.template["detected"]["trigger"])
            case "burn":
                self.send_msg(self.template["detected"]["burn"])
            case _:
                self.send_msg(self.template["detected"]["else"])

if __name__ == '__main__':
    sms_sender = SmsSender()
    sms_sender.set_info("", "")
    # sms_sender.send_msg(sms_sender.template["initial_text"]["current"][0])
    # sms_sender.send_msg(sms_sender.template["initial_text"]["current"][1])
    # sms_sender.send_msg(sms_sender.template["detected"]["trigger"])
    # sms_sender.send_msg(sms_sender.template["detected"]["burn"])
    # sms_sender.send_msg(sms_sender.template["detected"]["else"])
    # sms_sender.send_msg(sms_sender.template["detected"][0])
    # threading.Thread(target=sms_sender.read_msg).start()
