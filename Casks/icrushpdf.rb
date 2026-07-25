cask "icrushpdf" do
  version "1.1.0"
  sha256 "b47c7401a8ac884992eb015120dfc923a08e012b153934c846f7c8687dff8979"

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
