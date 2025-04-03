import subprocess
import os

directory = 'C:\\Users\\yashm\\Downloads\\platform-tools-latest-windows\\platform-tools'

# Define the adb command to be executed
command = [
    "adb", 
    "shell", 
    "am", 
    "startservice", 
    "--user", "0", 
    "-n", "com.android.shellms/.sendSMS", 
    "-e", "contact", "+14012346387", 
    "-e", "msg", "'Plant has been wounded'"
]

# Set the working directory to where adb is located
os.chdir(directory)

# Execute the command
try:
    subprocess.run(command, check=True)
    print("Message sent successfully.")
except subprocess.CalledProcessError as e:
    print(f"An error occurred: {e}")
