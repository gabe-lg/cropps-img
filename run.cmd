@echo off

call .\venv\Scripts\activate
set /p user_input=enter your arguments:

cd cropps-img
python main.py %user_input%

pause
