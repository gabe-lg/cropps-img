import subprocess
import os


class SmsSender:
    def __init__(self):
        # The path where adb was installed
        self.dir = ("C:\\Users\\CROPPS-in-Box\\Documents\\cropps main "
                    "folder\\platform-tools-latest-windows\\platform-tools")
        self.name = None
        self.phone = None
        self.phone_for_debug = "" #change

        oldpwd = os.getcwd()
        os.chdir(self.dir)

        try:
            # Increase the SMS sending limit
            subprocess.run([
                "adb", "shell", "settings", "put", "global",
                "sms_outgoing_check_max_count", "99999"
            ], check=True)

            # Increase the SMS sending interval window (in milliseconds)
            subprocess.run([
                "adb", "shell", "settings", "put", "global",
                "sms_outgoing_check_interval_ms", "9000000"
            ], check=True)

            print("SMS sending limit increased.")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")
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
        os.chdir(self.dir)

        # Execute the command
        try:
            subprocess.run(command, check=True)
            print(f"Message sent to {self.phone}: {message}")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")

        os.chdir(oldpwd)
