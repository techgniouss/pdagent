#!/bin/bash
# Quick setup script for Pocket Desk Agent

set -e

echo "=================================="
echo "Pocket Desk Agent Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
if command -v python &> /dev/null; then
    python_version=$(python --version 2>&1 | cut -d' ' -f2)
    python_major=$(echo "$python_version" | cut -d'.' -f1)
    python_minor=$(echo "$python_version" | cut -d'.' -f2)

    if [ "$python_major" -lt 3 ] || { [ "$python_major" -eq 3 ] && [ "$python_minor" -lt 11 ]; }; then
        echo "ERROR: Python 3.11+ required. Found: $python_version"
        exit 1
    fi
    echo "OK Python $python_version"
else
    echo "ERROR: Python not found. Please install Python 3.11+"
    exit 1
fi
echo ""

# Install package (editable so live reload picks up changes)
echo "Installing pocket-desk-agent in editable mode..."
pip install -e .
echo "OK Package installed (pdagent CLI available)"
echo ""

# Setup .env
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "OK .env created"
    echo ""
    echo "Please edit .env with your credentials:"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - TELEGRAM_BOT_USERNAME"
    echo "   - AUTHORIZED_USER_IDS"
    echo ""
else
    echo "OK .env already exists"
    echo ""
fi

# Check Tesseract OCR
echo "Checking Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    echo "OK Tesseract already installed ($(tesseract --version 2>&1 | head -1))"
else
    echo "Tesseract not found. Attempting install..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install -y tesseract-ocr 2>/dev/null && echo "OK Tesseract installed" || \
            echo "ERROR: Auto-install failed. Run: sudo apt-get install tesseract-ocr"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install tesseract 2>/dev/null && echo "OK Tesseract installed" || \
            echo "ERROR: Auto-install failed. Run: brew install tesseract"
    else
        echo "ERROR: Could not auto-install. On Windows use setup.bat, or download from:"
        echo "   https://github.com/UB-Mannheim/tesseract/wiki"
    fi
fi
echo ""

# Check if authenticated
if [ -f ~/.config/antigravity-chatbot/tokens.json ] || [ -f ~/.config/pdagent-gemini/tokens.json ] || [ -f ~/.gemini/oauth_creds.json ]; then
    echo "OK Already authenticated"
else
    echo "Authentication required"
    echo ""
    echo "Run: pdagent auth"
    echo "Choose an OAuth mode to authenticate with Gemini"
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your credentials"
echo "2. Run: pdagent auth (if not authenticated)"
echo "3. Run: pdagent"
echo ""
echo "For detailed instructions, see README.md"
