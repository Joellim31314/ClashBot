"""Calibration tool — captures a screenshot and overlays current config coordinates.

Usage:
    python calibrate.py              # Save screenshot + annotated version
    python calibrate.py --click      # Click mode: tap screen, see where it lands
"""
import sys
import io
import logging

from PIL import Image, ImageDraw, ImageFont
from ppadb.client import Client as AdbClient

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("calibrate")


def get_device():
    client = AdbClient(host=config.ADB_HOST, port=config.ADB_PORT)
    devices = client.devices()
    if not devices:
        logger.error("No ADB devices found. Is LDPlayer running?")
        sys.exit(1)
    return devices[0]


def capture_screenshot(device) -> Image.Image:
    png_bytes = device.screencap()
    return Image.open(io.BytesIO(png_bytes)).convert("RGB")


def annotate_screenshot(img: Image.Image) -> Image.Image:
    """Draw current config coordinates on the screenshot."""
    draw = ImageDraw.Draw(img)

    # Card slots — red circles
    for i, x in enumerate(config.CARD_SLOT_X):
        y = config.CARD_SLOT_Y
        r = 20
        draw.ellipse([x - r, y - r, x + r, y + r], outline="red", width=3)
        draw.text((x - 5, y - 35), f"Card {i}", fill="red")

    # Bridge positions — green circles
    for label, pos in [("L Bridge", config.LEFT_BRIDGE), ("R Bridge", config.RIGHT_BRIDGE)]:
        x, y = pos
        r = 15
        draw.ellipse([x - r, y - r, x + r, y + r], outline="lime", width=3)
        draw.text((x - 20, y - 25), label, fill="lime")

    # Battle button — blue
    bx, by = config.BATTLE_BUTTON
    r = 25
    draw.ellipse([bx - r, by - r, bx + r, by + r], outline="blue", width=3)
    draw.text((bx - 30, by - 35), "Battle", fill="blue")

    # OK button — cyan
    ox, oy = config.OK_BUTTON
    draw.ellipse([ox - r, oy - r, ox + r, oy + r], outline="cyan", width=3)
    draw.text((ox - 15, oy - 35), "OK", fill="cyan")

    # Elixir bar — yellow line
    draw.line(
        [(config.ELIXIR_BAR_X_START, config.ELIXIR_BAR_Y),
         (config.ELIXIR_BAR_X_END, config.ELIXIR_BAR_Y)],
        fill="yellow", width=3
    )
    draw.text((config.ELIXIR_BAR_X_START, config.ELIXIR_BAR_Y - 20), "Elixir Bar", fill="yellow")

    # Tower positions — orange
    towers = [
        ("EK", config.ENEMY_KING_TOWER),
        ("EL", config.ENEMY_LEFT_PRINCESS),
        ("ER", config.ENEMY_RIGHT_PRINCESS),
        ("FK", config.FRIENDLY_KING_TOWER),
        ("FL", config.FRIENDLY_LEFT_PRINCESS),
        ("FR", config.FRIENDLY_RIGHT_PRINCESS),
    ]
    for label, (tx, ty) in towers:
        draw.ellipse([tx - 10, ty - 10, tx + 10, ty + 10], outline="orange", width=2)
        draw.text((tx - 8, ty - 22), label, fill="orange")

    # Grid lines every 100px for reference
    for x in range(0, config.SCREEN_WIDTH, 100):
        draw.line([(x, 0), (x, config.SCREEN_HEIGHT)], fill=(50, 50, 50), width=1)
        draw.text((x + 2, 2), str(x), fill=(100, 100, 100))
    for y in range(0, config.SCREEN_HEIGHT, 100):
        draw.line([(0, y), (config.SCREEN_WIDTH, y)], fill=(50, 50, 50), width=1)
        draw.text((2, y + 2), str(y), fill=(100, 100, 100))

    return img


def main():
    device = get_device()

    logger.info("Capturing screenshot...")
    img = capture_screenshot(device)
    img.save("screenshot_raw.png")
    logger.info("Raw screenshot saved to screenshot_raw.png (%s)", img.size)

    annotated = annotate_screenshot(img.copy())
    annotated.save("screenshot_calibrate.png")
    logger.info("Annotated screenshot saved to screenshot_calibrate.png")
    logger.info("")
    logger.info("Open screenshot_calibrate.png and check:")
    logger.info("  - RED circles should be on the 4 card slots")
    logger.info("  - GREEN circles should be on the bridge tiles")
    logger.info("  - BLUE circle should be on the Battle button")
    logger.info("  - YELLOW line should be on the elixir bar")
    logger.info("")
    logger.info("If anything is off, note the correct coordinates from the grid")
    logger.info("and update config.py accordingly.")


if __name__ == "__main__":
    main()
