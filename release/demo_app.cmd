@echo off

cls
echo Plant Programming and Communication Project v3.0.0-beta
echo Opening demo version...

IF NOT EXIST ".setup_ok" (
    IF EXIST ".\setup.cmd" (
        call .\setup.cmd
    )
)

IF EXIST ".\venv\Scripts\activate" (
    call .\venv\Scripts\activate
)

IF EXIST "cropps-img" (
    cd cropps-img
)

IF EXIST "..\venv\Scripts\python.exe" (
    IF EXIST ".\main.py" (
        call "..\venv\Scripts\python.exe" main.py
    ) ELSE (
        echo Error: main.py not found
        exit /b 1
    )
) ELSE (
    echo Error: Failed to locate python executable
    exit /b 1
)

pause
