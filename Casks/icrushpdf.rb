cask "icrushpdf" do
  version "1.2.0"
  sha256 "5efc9770bf76dbf96171c1775fa38448e17780fe7b20c7fe8e2121a9bf23331f"

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
