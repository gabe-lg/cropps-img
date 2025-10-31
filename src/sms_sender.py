import difflib
import os
import queue
import re
import subprocess
import threading
import time


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
        self.init_ms = int(time.time() * 1000)
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
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")
        finally:
            os.chdir(oldpwd)

    def read_msg(self):
        """
        Continuously monitors text messages sent to the connected phone and
        prints a list of new messages received at every iteration.
        :param days_ago: Read messages received up to `days_ago` days ago.
        """

        # TODO: only read messages from the contact added in the box 
        while True:
            cmd = [
                './adb', 'shell', 'content', 'query',
                '--uri', 'content://sms/inbox',
                '--where', f'date\\>={self.init_ms}',
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
    
    def __fix_encoding(self, text: str) -> str:
        """
        Fix mis-decoded UTF-8 text that appears as Latin-1 (e.g., 'â€”' → '—', 'ðŸ”¥' → '🔥').
        """
        try:
            # Convert as if the text was incorrectly decoded from UTF-8 as Latin-1
            return text.decode('utf-8')
        except Exception:
            return text

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

        oldpwd = os.getcwd()
        os.chdir(self.dir)

        try:
            # Read received (inbox) messages
            inbox_cmd = [
                './adb', 'shell', 'content', 'query',
                '--uri', 'content://sms/inbox',
                '--projection', 'address,body,date',
                '--where', f"date\\>={self.init_ms}"
            ]
            inbox_output = subprocess.run(inbox_cmd, check=True, capture_output=True).stdout.decode("utf-8", errors="ignore")

            # Read sent messages
            sent_cmd = [
                './adb', 'shell', 'content', 'query',
                '--uri', 'content://sms/sent',
                '--projection', 'address,body,date',
                '--where', f"date\\>={self.init_ms}"
            ]
            sent_output = subprocess.run(sent_cmd, check=True, capture_output=True).stdout.decode("utf-8", errors="ignore")

        finally:
            os.chdir(oldpwd)

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
                    r"address=([^,]+),\s*body=(.*),\s*date=(\d+)", block, re.DOTALL
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


if __name__ == '__main__':
    sms_sender = SmsSender()
    # threading.Thread(target=sms_sender.read_msg).start()
