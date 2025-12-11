@echo off

cls
echo Plant Programming and Communication Project v2.1.0

IF NOT EXIST ".setup_ok" (
    call .\setup.cmd
)

call .\venv\Scripts\activate

if "%*"=="" (
    set /p user_input=enter arguments:
) else (
    set "user_input=%*"
)

cd cropps-img
call ..\venv\Scripts\python main.py %user_input%

pause
