@echo off

call .\setup.cmd
call .\venv\Scripts\activate
set /p user_input=enter your arguments:

cd cropps-img
call ..\venv\Scripts\python main.py %user_input%

pause
