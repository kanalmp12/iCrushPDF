cask "icrushpdf" do
  version "1.1.0"
  sha256 "52c32c45df55fd9e6ab546c4062dff70373ea4a4283d6423a2725a61d572b4c6"

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
