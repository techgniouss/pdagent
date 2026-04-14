@echo off
REM Quick setup script for Pocket Desk Agent (Windows)

echo ==================================
echo Pocket Desk Agent Setup
echo ==================================
echo.

REM Check Python
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python not found. Please install Python 3.11+
    exit /b 1
)
python --version
echo.

REM Install package in editable mode (pdagent CLI becomes available)
echo Installing pocket-desk-agent...
pip install -e .
if errorlevel 1 (
    echo X Failed to install package
    exit /b 1
)
echo OK Package installed (pdagent CLI available)
echo.

REM Setup .env
if not exist .env (
    echo Creating .env file...
    copy .env.example .env
    echo √ .env created
    echo.
    echo ! Please edit .env with your credentials:
    echo    - TELEGRAM_BOT_TOKEN
    echo    - TELEGRAM_BOT_USERNAME
    echo    - AUTHORIZED_USER_IDS
    echo.
) else (
    echo √ .env already exists
    echo.
)

REM Check / install Tesseract OCR
echo Checking Tesseract OCR...
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo Tesseract not found. Attempting install via winget...
    winget install UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
    if errorlevel 1 (
        echo ! winget install failed. Install Tesseract manually:
        echo   https://github.com/UB-Mannheim/tesseract/wiki
    ) else (
        echo OK Tesseract installed successfully
    )
) else (
    echo OK Tesseract already installed
)
echo.

REM Check authentication
if exist "%USERPROFILE%\.config\antigravity-chatbot\tokens.json" (
    echo OK Already authenticated
) else (
    if exist "%USERPROFILE%\.config\pdagent-gemini\tokens.json" (
        echo OK Already authenticated
    ) else (
        if exist "%USERPROFILE%\.gemini\oauth_creds.json" (
            echo OK Already authenticated
        ) else (
            echo ! Authentication required
            echo.
            echo Run: pdagent auth
            echo Choose an OAuth mode to authenticate with Gemini
        )
    )
)

echo.
echo ==================================
echo Setup Complete!
echo ==================================
echo.
echo Next steps:
echo 1. Edit .env with your credentials
echo 2. Run: pdagent auth (if not authenticated^)
echo 3. Run: pdagent
echo.
echo For detailed instructions, see README.md
pause
