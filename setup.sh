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
        echo "❌ Python 3.11+ required. Found: $python_version"
        exit 1
    fi
    echo "✅ Python $python_version"
else
    echo "❌ Python not found. Please install Python 3.11+"
    exit 1
fi
echo ""

# Install package (editable so live reload picks up changes)
echo "Installing pocket-desk-agent in editable mode..."
pip install -e .
echo "✅ Package installed (pdagent CLI available)"
echo ""

# Setup .env
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✅ .env created"
    echo ""
    echo "⚠️  Please edit .env with your credentials:"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - TELEGRAM_BOT_USERNAME"
    echo "   - AUTHORIZED_USER_IDS"
    echo ""
else
    echo "✅ .env already exists"
    echo ""
fi

# Check Tesseract OCR
echo "Checking Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract already installed ($(tesseract --version 2>&1 | head -1))"
else
    echo "⚠️  Tesseract not found. Attempting install..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install -y tesseract-ocr 2>/dev/null && echo "✅ Tesseract installed" || \
            echo "❌ Auto-install failed. Run: sudo apt-get install tesseract-ocr"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install tesseract 2>/dev/null && echo "✅ Tesseract installed" || \
            echo "❌ Auto-install failed. Run: brew install tesseract"
    else
        echo "❌ Could not auto-install. On Windows use setup.bat, or download from:"
        echo "   https://github.com/UB-Mannheim/tesseract/wiki"
    fi
fi
echo ""

# Check if authenticated
if [ -f ~/.pdagent/tokens.json ]; then
    echo "✅ Already authenticated"
else
    echo "⚠️  Authentication required"
    echo ""
    echo "Run: pdagent auth"
    echo "Select option 1 to authenticate with Google"
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
