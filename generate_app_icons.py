import os
from pathlib import Path
from PIL import Image

BRAIN_DIR = Path(r"C:\Users\heito\.gemini\antigravity\brain\da4ff062-7090-4a3a-8b02-9789d5fd39b7")
SOURCE_IMG = BRAIN_DIR / "lavender_icepick_angled_1788458032280.jpg"

BASE_DIR = Path(__file__).resolve().parent
MOBILE_DIR = BASE_DIR / "mobile"
UI_DIR = BASE_DIR / "ui"

def main():
    if not SOURCE_IMG.exists():
        print(f"Error: {SOURCE_IMG} does not exist")
        return

    img = Image.open(SOURCE_IMG).convert("RGBA")
    
    # 1. mobile/icon-512.png
    icon_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
    icon_512.save(MOBILE_DIR / "icon-512.png", "PNG")
    print("Saved mobile/icon-512.png")

    # 2. mobile/icon-192.png
    icon_192 = img.resize((192, 192), Image.Resampling.LANCZOS)
    icon_192.save(MOBILE_DIR / "icon-192.png", "PNG")
    print("Saved mobile/icon-192.png")

    # 3. mobile/apple-touch-icon.png (180x180 for iOS)
    apple_icon = img.resize((180, 180), Image.Resampling.LANCZOS)
    apple_icon.save(MOBILE_DIR / "apple-touch-icon.png", "PNG")
    print("Saved mobile/apple-touch-icon.png")

    # 4. ui/favicon.png (64x64)
    fav_png = img.resize((64, 64), Image.Resampling.LANCZOS)
    fav_png.save(UI_DIR / "favicon.png", "PNG")
    print("Saved ui/favicon.png")

    # 5. ui/favicon.ico
    fav_png.save(UI_DIR / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("Saved ui/favicon.ico")

if __name__ == "__main__":
    main()
