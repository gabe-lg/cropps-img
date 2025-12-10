@echo off

IF NOT EXIST ".\venv\Scripts\activate" (
    echo Creating virtual environment...
    python -m venv .\venv
    IF %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to create virtual environment
        exit /b 1
    )
) ELSE (
    echo Virtual environment already exists.
)

echo Activating virtual environment...
call .\venv\Scripts\activate
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to activate the virtual environment
    exit /b 1
)

IF NOT EXIST "cropps-img" (
    echo Cloning repository...
    git clone https://github.com/gabe-lg/cropps-img
    IF %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to clone repository
        exit /b 1
    )
) ELSE (
    echo Repository 'cropps-img' already exists
)

echo Installing dependencies...
python -m pip install -r cropps-img/requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install dependencies
    exit /b 1
)

IF EXIST "dlls" (
    echo Moving dlls...
    move dlls cropps-img
) ELSE (
    IF NOT EXIST "cropps-img/dlls" (
        echo Error: folder 'dlls' missing
        exit /b 1
    )
)

IF EXIST "platform-tools" (
    echo Moving platform-tools...
    move platform-tools cropps-img
) ELSE (
    IF NOT EXIST "cropps-img/platform-tools" (
        echo Error: folder 'platform-tools' missing
        exit /b 1
    )
)

echo Setup done!
pause
