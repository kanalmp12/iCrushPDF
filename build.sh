#!/bin/bash

# Ensure we are in the script's directory
cd "$(dirname "$0")"

echo "Activating virtual environment..."
if [ ! -d "../venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv ../venv
fi
source ../venv/bin/activate

echo "Installing requirements..."
pip install PyMuPDF customtkinter pyinstaller

echo "Building MacOS App Bundle with PyInstaller..."
# We use --windowed to create a .app bundle without a console window
# --name sets the app name
# --add-data allows including extra resources if needed (CustomTkinter sometimes needs this)
# Actually, customtkinter in newer pyinstaller versions is handled automatically.

export PYINSTALLER_CONFIG_DIR="$(pwd)/.pyinstaller_cache"
# Note: Once you have an icon (e.g. icon.icns), add --icon="icon.icns" to the command below
pyinstaller --noconfirm \
            --windowed \
            --name "iCrushPDF" \
            --icon="icon.icns" \
            --clean \
            compressor.py

echo "Build complete! The app is located in the 'dist' folder."
