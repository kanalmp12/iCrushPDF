cask "icrushpdf" do
  version "1.2.0"
  sha256 "8f9053b72cb5b272337e0fb2290d5abb1b5e3ca3a67fdd56c5822651fca1056c"

  # Download URL pointing to GitHub releases
  url "https://github.com/kanalmp12/iCrushPDF/releases/download/v#{version}/iCrushPDF-v#{version}.zip"
  name "iCrushPDF"
  desc "Lightning-fast, private, on-device macOS PDF compressor app"
  homepage "https://github.com/kanalmp12/iCrushPDF"

  depends_on macos: :monterey

  app "iCrushPDF.app"

  # Automatically remove macOS Gatekeeper quarantine flags so users can open the app without alerts
  postflight do
    system_command "xattr",
                   args: ["-cr", "#{appdir}/iCrushPDF.app"],
                   sudo: false
  end

  zap trash: [
    "~/Library/Preferences/com.icrushpdf.app.plist",
  ]
end
