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
pip install PyMuPDF customtkinter pyinstaller tkinterdnd2

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
            --collect-all tkinterdnd2 \
            --clean \
            compressor.py

APP_VERSION="1.1.0"
echo "Injecting native macOS Info.plist metadata (Version $APP_VERSION)..."
plutil -replace CFBundleShortVersionString -string "$APP_VERSION" dist/iCrushPDF.app/Contents/Info.plist
plutil -replace CFBundleVersion -string "$APP_VERSION" dist/iCrushPDF.app/Contents/Info.plist
plutil -replace CFBundleIdentifier -string "com.icrushpdf.app" dist/iCrushPDF.app/Contents/Info.plist
plutil -replace CFBundleName -string "iCrushPDF" dist/iCrushPDF.app/Contents/Info.plist
plutil -replace CFBundleDisplayName -string "iCrushPDF" dist/iCrushPDF.app/Contents/Info.plist
plutil -replace NSHumanReadableCopyright -string "Copyright © 2026 iCrushPDF. All rights reserved." dist/iCrushPDF.app/Contents/Info.plist

echo "Build complete! The app is located in the 'dist' folder with version $APP_VERSION."
