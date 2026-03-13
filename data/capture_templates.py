"""Capture card template images from the emulator.

Connects to LDPlayer via ADB, takes a screenshot, and crops each of the
4 card slots into individual PNG files for template matching.

Usage:
    python data/capture_templates.py [--name CARD_NAME]

If --name is given, saves as data/card_templates/<name>.png (slot 0 only).
Otherwise, saves as data/card_templates/slot_0.png ... slot_3.png.
"""
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from bot.screen import ScreenCapture

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def crop_card_slot(image, slot: int):
    """Crop a single card slot region from the screenshot."""
    cx = config.CARD_SLOT_X[slot]
    cy = config.CARD_SLOT_Y
    w = config.CARD_CROP_WIDTH
    h = config.CARD_CROP_HEIGHT
    y_off = config.CARD_CROP_Y_OFFSET

    left = cx - w // 2
    top = cy + y_off
    right = left + w
    bottom = top + h

    return image.crop((left, top, right, bottom))


def main():
    parser = argparse.ArgumentParser(description="Capture card templates from emulator")
    parser.add_argument("--name", type=str, default=None,
                        help="Card name (saves slot 0 as <name>.png)")
    parser.add_argument("--all", action="store_true",
                        help="Capture all 4 slots")
    args = parser.parse_args()

    template_dir = Path(config.CARD_TEMPLATE_DIR)
    template_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to emulator...")
    screen = ScreenCapture()
    if not screen.is_connected():
        logger.error("Cannot connect to emulator. Is LDPlayer running?")
        sys.exit(1)

    logger.info("Capturing screenshot...")
    image = screen.capture()
    logger.info("Screenshot size: %dx%d", image.width, image.height)

    if args.name:
        # Save just slot 0 with the given name
        crop = crop_card_slot(image, 0)
        save_path = template_dir / f"{args.name}.png"
        crop.save(save_path)
        logger.info("Saved card template: %s (%dx%d)", save_path, crop.width, crop.height)
    else:
        # Save all 4 slots
        for slot in range(4):
            crop = crop_card_slot(image, slot)
            save_path = template_dir / f"slot_{slot}.png"
            crop.save(save_path)
            logger.info("Saved slot %d: %s (%dx%d)", slot, save_path, crop.width, crop.height)

    logger.info("Done! Templates saved to %s", template_dir)
    logger.info("To build your template library:")
    logger.info("  1. Start a battle, wait for cards to appear")
    logger.info("  2. Run: python data/capture_templates.py --name knight")
    logger.info("  3. Repeat for each card in your deck")


if __name__ == "__main__":
    main()
