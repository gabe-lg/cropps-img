import subprocess
import os


class SmsSender:
    def __init__(self):
        # The path where adb was installed
        self.dir = ("C:\\Users\\CROPPS-in-Box\\Documents\\cropps main "
                    "folder\\platform-tools-latest-windows\\platform-tools")
        self.name = None
        self.phone = None

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
        if self.name is not None and self.phone is not None:
            # Create the message dynamically
            message = f"Hi {self.name}, the plant has been wounded"

            # Define the adb command to be executed
            command = [
                "./adb",
                "shell",
                "am",
                "startservice",
                "--user", "0",
                "-n", "com.android.shellms/.sendSMS",
                "-e", "contact", self.phone,
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
            return 0
        return 1
