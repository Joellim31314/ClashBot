"""Generate synthetic YOLO training data from sprite library.

Composites transparent sprite PNGs onto arena background screenshots
to create labeled training images in YOLO format.

Prerequisites:
    1. Clone sprite library: git clone https://github.com/wty-yy/Clash-Royale-Detection-Dataset data/sprites
    2. Capture 5-10 clean arena backgrounds from the emulator (no troops)
       Save to data/backgrounds/

Usage:
    python data/generate_training_data.py [--count 2000] [--output data/yolo_dataset]
"""
import argparse
import logging
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
from PIL import Image

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Arena bounds where troops can be placed (relative to 1080x2400)
# These define the playable area, excluding UI elements
ARENA_Y_MIN = 200   # Top of arena (near enemy king tower)
ARENA_Y_MAX = 1800  # Bottom of arena (near friendly towers)
ARENA_X_MIN = 50
ARENA_X_MAX = 1030

# Sprite scale range (fraction of original size)
SPRITE_SCALE_MIN = 0.4
SPRITE_SCALE_MAX = 1.2


def load_sprites(sprite_dir: str) -> dict[str, list[Path]]:
    """Load all sprite paths organized by class name.

    Expected structure: data/sprites/<class_name>/*.png
    """
    sprite_dir = Path(sprite_dir)
    if not sprite_dir.exists():
        logger.error("Sprite directory not found: %s", sprite_dir)
        logger.info("Clone: git clone https://github.com/wty-yy/Clash-Royale-Detection-Dataset data/sprites")
        sys.exit(1)

    sprites = {}
    for class_dir in sorted(sprite_dir.iterdir()):
        if not class_dir.is_dir():
            continue
        pngs = sorted(class_dir.glob("*.png"))
        if pngs:
            sprites[class_dir.name] = pngs

    logger.info("Loaded %d classes, %d total sprites",
                len(sprites), sum(len(v) for v in sprites.values()))
    return sprites


def load_backgrounds(bg_dir: str) -> list[Image.Image]:
    """Load arena background images."""
    bg_dir = Path(bg_dir)
    if not bg_dir.exists():
        logger.error("Background directory not found: %s", bg_dir)
        logger.info("Capture clean arena screenshots (no troops) and save to data/backgrounds/")
        sys.exit(1)

    backgrounds = []
    for img_path in sorted(bg_dir.glob("*.png")):
        img = Image.open(img_path).convert("RGB")
        backgrounds.append(img)

    if not backgrounds:
        logger.error("No background images found in %s", bg_dir)
        sys.exit(1)

    logger.info("Loaded %d background images", len(backgrounds))
    return backgrounds


def paste_sprite(background: Image.Image, sprite_path: Path,
                 x: int, y: int, scale: float) -> tuple[int, int, int, int] | None:
    """Paste a sprite onto the background at (x, y) with given scale.

    Returns (x1, y1, x2, y2) bounding box or None if sprite is invalid.
    """
    sprite = Image.open(sprite_path).convert("RGBA")

    # Scale sprite
    new_w = max(1, int(sprite.width * scale))
    new_h = max(1, int(sprite.height * scale))
    sprite = sprite.resize((new_w, new_h), Image.LANCZOS)

    # Calculate paste position (centered at x, y)
    paste_x = x - new_w // 2
    paste_y = y - new_h // 2

    # Clip to image bounds
    bg_w, bg_h = background.size
    x1 = max(0, paste_x)
    y1 = max(0, paste_y)
    x2 = min(bg_w, paste_x + new_w)
    y2 = min(bg_h, paste_y + new_h)

    if x2 - x1 < 5 or y2 - y1 < 5:
        return None  # Too small after clipping

    # Paste with alpha mask
    background.paste(sprite, (paste_x, paste_y), sprite)

    return (x1, y1, x2, y2)


def bbox_to_yolo(bbox: tuple[int, int, int, int],
                 img_w: int, img_h: int) -> tuple[float, float, float, float]:
    """Convert (x1, y1, x2, y2) to YOLO format (cx, cy, w, h) normalized."""
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2.0 / img_w
    cy = (y1 + y2) / 2.0 / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return (cx, cy, w, h)


def generate_image(backgrounds: list[Image.Image],
                   sprites: dict[str, list[Path]],
                   class_to_id: dict[str, int],
                   num_sprites: tuple[int, int] = (5, 15)) -> tuple[Image.Image, list[str]]:
    """Generate one synthetic training image with YOLO labels.

    Returns (image, list of YOLO label lines).
    """
    bg = random.choice(backgrounds).copy()
    img_w, img_h = bg.size

    n = random.randint(*num_sprites)
    class_names = list(sprites.keys())
    labels = []

    for _ in range(n):
        cls_name = random.choice(class_names)
        if cls_name not in class_to_id:
            continue

        sprite_path = random.choice(sprites[cls_name])
        x = random.randint(ARENA_X_MIN, ARENA_X_MAX)
        y = random.randint(ARENA_Y_MIN, ARENA_Y_MAX)
        scale = random.uniform(SPRITE_SCALE_MIN, SPRITE_SCALE_MAX)

        bbox = paste_sprite(bg, sprite_path, x, y, scale)
        if bbox is None:
            continue

        cx, cy, w, h = bbox_to_yolo(bbox, img_w, img_h)
        cls_id = class_to_id[cls_name]
        labels.append(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

    return bg, labels


def build_class_map(sprites: dict[str, list[Path]]) -> dict[str, int]:
    """Build class name -> ID mapping from available sprites."""
    class_names = sorted(sprites.keys())
    return {name: i for i, name in enumerate(class_names)}


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic YOLO training data")
    parser.add_argument("--count", type=int, default=2000,
                        help="Number of training images to generate")
    parser.add_argument("--output", type=str, default="data/yolo_dataset",
                        help="Output directory for dataset")
    parser.add_argument("--sprites", type=str, default="data/sprites",
                        help="Path to sprite library")
    parser.add_argument("--backgrounds", type=str, default="data/backgrounds",
                        help="Path to background screenshots")
    parser.add_argument("--val-split", type=float, default=0.15,
                        help="Fraction of data for validation")
    args = parser.parse_args()

    sprites = load_sprites(args.sprites)
    backgrounds = load_backgrounds(args.backgrounds)
    class_to_id = build_class_map(sprites)

    logger.info("Class mapping: %d classes", len(class_to_id))

    # Create output directories
    output = Path(args.output)
    train_img_dir = output / "images" / "train"
    train_lbl_dir = output / "labels" / "train"
    val_img_dir = output / "images" / "val"
    val_lbl_dir = output / "labels" / "val"

    for d in [train_img_dir, train_lbl_dir, val_img_dir, val_lbl_dir]:
        d.mkdir(parents=True, exist_ok=True)

    val_count = int(args.count * args.val_split)
    train_count = args.count - val_count

    logger.info("Generating %d train + %d val images...", train_count, val_count)

    for i in range(args.count):
        image, labels = generate_image(backgrounds, sprites, class_to_id)

        if i < train_count:
            img_dir, lbl_dir = train_img_dir, train_lbl_dir
        else:
            img_dir, lbl_dir = val_img_dir, val_lbl_dir

        img_path = img_dir / f"synth_{i:05d}.png"
        lbl_path = lbl_dir / f"synth_{i:05d}.txt"

        image.save(img_path)
        lbl_path.write_text("\n".join(labels) + "\n" if labels else "")

        if (i + 1) % 100 == 0:
            logger.info("Generated %d / %d images", i + 1, args.count)

    # Save class names file
    class_names_path = output / "classes.txt"
    id_to_name = {v: k for k, v in class_to_id.items()}
    class_names_path.write_text(
        "\n".join(id_to_name[i] for i in range(len(id_to_name))) + "\n"
    )

    logger.info("Dataset generated at %s", output)
    logger.info("Classes: %d, Train: %d, Val: %d", len(class_to_id), train_count, val_count)
    logger.info("Next: run python data/train_yolo.py to train the model")


if __name__ == "__main__":
    main()
