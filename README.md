<a id="readme-top"></a>

<!-- PROJECT LOGO -->
<div align="center">
  <a>
    <img src="assets/cropps_watermark.png" alt="Logo" width="500" height="250">
  </a>
</div>


<!-- ABOUT THE PROJECT -->
## Plant Programming and Communication Project 
This project aims to tackle the challenge of sustainable food production in the face of climate change by developing programmable plants that can emit and respond to optical, electrical, and mechanical signals. It involves creating a portable, automated system capable of interacting with these "programmable" plants, combining expertise in robotics, sensing, imaging, and plant biology. Our primary goal is to develop a system that can detect the fluorescent signals emitted by plants when they are cut or squeezed, and alert the user to the plant's injury. The software objectives for this project are outlined as follows, and this repository contains all the code and setup required for these functions:

- Design an imaging setup using a USB Dino Lite microscope to visualize fluorescent signals from Arabidopsis thaliana plants
- Interface the USB microscope firmware with a computer
- Develop code to track and extract data from the fluorescence images, such as signal intensity and velocity
- Design a wireless communication module that sends an SMS notification when a fluorescent signal is detected

<!-- SOFTWARE TOOLS INFO -->
## Software Tools
- **Dino Lite SDK (https://www.dino-lite.com/download06.php)** <br>
  A software development kit for the Dino Lite microscrope that allows for control of the the microsope through C#, C++ and Visual Basic code. Please use the 64 bit version since it is compatible with the 
  python module mentioned next. 
- **Dino Lite SDK Python Wrapper: https://github.com/dino-lite/DNX64-Python-API**<br>
  Python Wrapper that works with the Dino Lite SDK and contains multiple python function to capture images, set microscope exposure, start recording etc.
- **Shell MS: https://github.com/try2codesecure/ShellMS?tab=readme-ov-file**<br>
  Shell SMS Application that can send messages from a connected Android by running commands on the terminal
- **ADB for Windows:** https://dl.google.com/android/repository/platform-tools-latest-windows.zip<br>
  Android Debug Bridge for Windows needed to run the shell MS Application 


<!-- GETTING STARTED -->
## Getting Started 
To replicate this project on your computer please do the following:
1. Download all the software Tools mentioned above
2. Keep track of the paths of the following files/folders to define in the code:
   - DNX64.dll file which is part of the Dino Lite SDK download
   - platform-windows folder of ADB
3. Git clone the repo https://github.com/gabe-lg/cropps-img.git
4. Install all the libraries mentioned in requirements.txt by running the pip install -r requirements.txt command in the terminal 
5. In main.py replace the DNX64_PATH with the path to your DNX64.dll file
6. In send_sms.py replace working_directory with the path to your platform-windows folder
7. Connect the Dino Lite microscope to your computer via USB. **Note:** You might need to disable the built in camera on you computer to access the microscope view
8. Connect an android phone to the computer via an appropriate cable and click "Allow" if a popup appears for USB Debugging
9. Run the main.py file using the command python main.py in the terminal

<!-- OUTPUT OF MAIN.PY -->
## Output 
Once the main.py file is run you should see that following GUI open up<br>
<img src="/assets/demo.jpg" alt="demo"> <br>
The buttons on the GUI have the following functionality:
- **Print AMR**: prints the Automatic Magnification Reading (AMR)
- **Flash LEDS**: flashed the micoscope LEDs
- **Print FOV**: prints the Field of View (FOV) in micrometers
- **Capture Image**: Captures current frame and opens the captured frame in a different window
- **Start Analysis/Stop Analysis**: Starts or Stops the image analysis that looks for a flourensence signal in the plant indicating agitation
- **Start/Stop recording**: Starts taking a video
- **Set Exposure**: Sets the exposure value, for best results in image analysis set exposure around **[Enter a value here]**
- **SMS Info**: Opens up a dialog box in which the name and contact information of a user can be saved so they will recieve texts when the plant has been wounded
- **Exit**: Closes the GUI and terminates run of main.py


