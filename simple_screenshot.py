"""
Simple Screenshot Tool for ClashBot.

Captures a single screenshot from the emulator and saves it to data/screenshots.

Usage:
    python simple_screenshot.py
"""
import sys
from datetime import datetime
from pathlib import Path

import config
from bot.screen import ScreenCapture


def main():
    print("Connecting to emulator...")
    try:
        sc = ScreenCapture()
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    if not sc.is_connected():
        print("No device found. Is LDPlayer running with ADB enabled?")
        sys.exit(1)

    print("Capturing screenshot...")
    image = sc.capture()
    print(f"Screenshot size: {image.size}")

    if image.size != (config.SCREEN_WIDTH, config.SCREEN_HEIGHT):
        print(f"WARNING: Expected {config.SCREEN_WIDTH}x{config.SCREEN_HEIGHT}, "
              f"got {image.size[0]}x{image.size[1]}!")
        print("Emulator resolution may be incorrect.")

    out_dir = Path("data") / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"screenshot_{timestamp}.png"
    image.save(out_path)
    print(f"Saved screenshot to {out_path}")


if __name__ == "__main__":
    main()
