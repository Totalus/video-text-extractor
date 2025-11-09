#!/bin/bash
# Installation and Setup Script for Video Text Extractor
# This script helps automate the installation process

set -e  # Exit on error

echo "========================================"
echo "Video Text Extractor - Setup Script"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Check if Python 3.7+
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)"; then
    echo "✓ Python version is compatible"
else
    echo "✗ Python 3.7+ is required"
    exit 1
fi
echo ""

# Check if Tesseract is installed
echo "Checking for Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    tesseract_version=$(tesseract --version 2>&1 | head -n 1)
    echo "✓ $tesseract_version"
else
    echo "✗ Tesseract OCR is not installed"
    echo ""
    echo "Please install Tesseract OCR first:"
    echo "  Ubuntu/Debian: sudo apt-get update && sudo apt-get install tesseract-ocr"
    echo "  Fedora/RHEL:   sudo dnf install tesseract"
    echo "  Arch Linux:    sudo pacman -S tesseract"
    echo "  macOS:         brew install tesseract"
    echo ""
    read -p "Continue without Tesseract? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# Check if pip is available
echo "Checking for pip..."
if command -v pip3 &> /dev/null; then
    echo "✓ pip3 is available"
elif command -v pip &> /dev/null; then
    echo "✓ pip is available"
else
    echo "✗ pip is not installed"
    echo "Please install pip: python3 -m ensurepip --upgrade"
    exit 1
fi
echo ""

# Ask if user wants to create virtual environment
echo "Would you like to create a virtual environment? (Recommended)"
read -p "Create virtual environment? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
    echo ""
    echo "To activate the virtual environment, run:"
    echo "  source venv/bin/activate"
    echo ""
    read -p "Activate now and continue installation? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        source venv/bin/activate
        echo "✓ Virtual environment activated"
    else
        echo "Please activate the virtual environment and run: pip install -r requirements.txt"
        exit 0
    fi
fi
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✓ Dependencies installed"
else
    echo "✗ requirements.txt not found"
    exit 1
fi
echo ""

# Run dependency check
echo "Running dependency check..."
python check_dependencies.py
check_result=$?
echo ""

# Final message
if [ $check_result -eq 0 ]; then
    echo "========================================"
    echo "✓ Setup Complete!"
    echo "========================================"
    echo ""
    echo "You're ready to use the video_text_extractor!"
    echo ""
    echo "Quick start:"
    echo "  python video_text_extractor.py your_video.mp4"
    echo ""
    echo "For more information:"
    echo "  python video_text_extractor.py --help"
    echo "  cat README.md"
    echo "  cat QUICKSTART.md"
    echo ""
else
    echo "========================================"
    echo "⚠ Setup Incomplete"
    echo "========================================"
    echo ""
    echo "Some dependencies are missing. Please review the errors above."
    echo "You may need to:"
    echo "  1. Install Tesseract OCR"
    echo "  2. Activate your virtual environment"
    echo "  3. Run: pip install -r requirements.txt"
    echo ""
fi
