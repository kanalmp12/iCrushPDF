# 💘 iCrushPDF

**Lightning-Fast, Private, On-Device macOS PDF Compressor App**

![macOS](https://img.shields.io/badge/macOS-12.0%2B-000000?style=for-the-badge&logo=apple)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

Why upload your sensitive documents to online cloud servers when you can crush their file sizes locally in seconds? **iCrushPDF** gives you maximum compression savings without ever leaving your Mac.

---

## ✨ Why iCrushPDF?

- 🔒 **100% On-Device & Private:** Powered locally by PyMuPDF engine—your private files never get sent over the internet.
- 📦 **Native Drag & Drop:** Drop PDF files anywhere onto the application window or directly onto the app Dock/Finder icon to instantly open and prepare for compression.
- 🎨 **Real-Time macOS Theme Sync:** Automatically detects and conforms to your system Accent Color (Pink, Green, Orange, Purple, etc.) and Dark/Light mode in real-time.
- ⚡ **Asymptotic Progress UI:** Smooth, lively status feedback with intuitive visual state indicators and instant Finder reveal.
- 🛠️ **Minimal Footprint:** Built natively for macOS Apple Silicon & Intel architectures.

---

## 🚀 Installation via Homebrew (Recommended)

You can easily install **iCrushPDF** on your Mac via two simple methods:

### Method 1: Tap & Install (Shorthand Command)
Add our custom repository to your Homebrew tap, trust it, and install in seconds:

```bash
brew tap kanalmp12/icrushpdf https://github.com/kanalmp12/iCrushPDF.git
brew trust kanalmp12/icrushpdf
brew install --cask icrushpdf
```

### Method 2: Direct URL Install (One-Liner)
Or simply install directly from our formula URL without setting up a tap:

```bash
brew install --cask https://raw.githubusercontent.com/kanalmp12/iCrushPDF/main/icrushpdf.rb
```

> 💡 **Note:** The installation formula automatically removes macOS Gatekeeper download restrictions (`xattr -cr`) after installation, allowing you to launch **iCrushPDF** immediately without any pop-up warnings!

---

## 🛠️ Building From Source

You can effortlessly build the standalone macOS Application bundle (`.app`) on your own machine:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kanalmp12/iCrushPDF.git
   cd iCrushPDF
   ```

2. **Run the one-click build script:**
   ```bash
   chmod +x build.sh
   ./build.sh
   ```
   *The script automatically sets up an isolated Python virtual environment, installs required libraries, applies custom Apple icon assets (`.icns`), and compiles `iCrushPDF.app` directly into the `dist/` folder.*

---

## 📝 License
MIT License. Created with 💖 for macOS users everywhere.
