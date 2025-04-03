import subprocess
import os

# Define the path where adb works
working_directory ='C:\\Users\\yashm\\Downloads\\platform-tools-latest-windows\\platform-tools'

# Get user input for phone number and name
phone_number = "+1" + input("Enter the phone number (e.g., 1234567890): ")
name = input("Enter the name: ")

# Create the message dynamically
message = f"Hi {name}, the plant has been wounded"

# Define the adb command to be executed
command = [
    "./adb", 
    "shell", 
    "am", 
    "startservice", 
    "--user", "0", 
    "-n", "com.android.shellms/.sendSMS", 
    "-e", "contact", phone_number, 
    "-e", "msg", f"'{message}'"
]

# Change the current working directory to where adb works
os.chdir(working_directory)

# Execute the command
try:
    subprocess.run(command, check=True)
    print(f"Message sent to {phone_number}: {message}")
except subprocess.CalledProcessError as e:
    print(f"An error occurred: {e}")
