import difflib
import os
import queue
import subprocess
import threading
from datetime import datetime, time, timedelta


class SmsSender:
    def __init__(self):
        # The path where adb was installed
        self.dir = ("C:\\Users\\CROPPS-in-Box\\Documents\\cropps main "
                    "folder\\platform-tools-latest-windows\\platform-tools")
        self.name = None
        self.phone = None
        self.phone_for_debug = ""  # change
        self.sms_msgs = ""  # full output
        self.new_msg_event = threading.Event()
        self.new_msgs = queue.Queue()  # individual msgs

        oldpwd = os.getcwd()
        try:
            os.chdir(self.dir)
        except FileNotFoundError:
            self.dir = input("Enter the path where adb is installed: ")
            os.chdir(self.dir)

        try:
            # Increase the SMS sending limit
            subprocess.run([
                "./adb", "shell", "settings", "put", "global",
                "sms_outgoing_check_max_count", "99999"
            ], check=True)

            # Increase the SMS sending interval window (in milliseconds)
            subprocess.run([
                "./adb", "shell", "settings", "put", "global",
                "sms_outgoing_check_interval_ms", "9000000"
            ], check=True)

            print("SMS sending limit increased.")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")
        finally:
            os.chdir(oldpwd)

    def set_info(self, contact_name: str, contact_phone: str):
        """
        Sets `name` and `phone`.
        """
        self.name = contact_name
        self.phone = contact_phone

    def send_sms(self) -> int:
        """
        Sends an sms message to `phone`.
        Returns: 0 if successful; otherwise 1
        """
        if not (self.name and self.phone): return 1
        self.send_msg(self.phone,
                      f"Hi {self.name}, I’m hurt! Please help 😱😱")
        return 0

    def send_debug_msg(self, message: str):
        self.send_msg(self.phone_for_debug, message)

    def send_msg(self, phone, message):
        command = [
            "./adb",
            "shell",
            "am",
            "startservice",
            "--user", "0",
            "-n", "com.android.shellms/.sendSMS",
            "-e", "contact", phone,
            "-e", "msg", f"'{message}'"
        ]

        # Change the current working directory to where adb works
        oldpwd = os.getcwd()

        # Execute the command
        try:
            os.chdir(self.dir)
            subprocess.run(command, check=True)
            print(f"Message sent to {self.phone}: {message}")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")
        finally:
            os.chdir(oldpwd)

    def read_msg(self, days_ago: int = 0):
        """
        Continuously monitors text messages sent to the connected phone and
        prints a list of new messages received at every iteration.
        :param days_ago: Read messages received up to `days_ago` days ago.
        """
        while True:
            now_ms = int(
                datetime.combine(
                    datetime.now().date() - timedelta(days=days_ago),
                    time(0, 0, 0)).timestamp() * 1000)

            cmd = [
                './adb', 'shell', 'content', 'query',
                '--uri', 'content://sms/inbox',
                '--where', f'date\\>={now_ms}',
                '--projection', 'body'
            ]

            os.chdir(self.dir)
            output = subprocess.run(cmd, check=True, capture_output=True,
                                    text=True).stdout

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

            self.sms_msgs = output


if __name__ == '__main__':
    os.chdir(("C:\\Users\\CROPPS-in-Box\\Documents\\cropps main "
              "folder\\platform-tools-latest-windows\\platform-tools"))
    sms_sender = SmsSender()
    sms_sender.set_info("Test", "0")
    sms_sender.send_sms()
    threading.Thread(target=sms_sender.read_msg, args=(2,)).start()
