"""Inspect YOLO detections on screenshots — troops only, clean output.

Saves annotated images with only troop/building detections (no health bars,
elixir numbers, etc.) and writes a text summary for manual review.

Usage:
    python data/inspect_detections.py [--conf 0.3]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vendor" / "KataCR"))

import torch
_orig = torch.load
def _patched(*a, **kw):
    kw.setdefault("weights_only", False)
    return _orig(*a, **kw)
torch.load = _patched

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

# Classes to hide from the visual (UI noise)
UI_CLASSES = {
    "tower-bar", "bar", "bar-level", "elixir", "emote", "clock",
    "padding_belong", "evolution-symbol", "ice-spirit-evolution-symbol",
    "skeleton-king-bar", "selected", "text", "king-tower-bar",
    "dagger-duchess-tower-bar",
}

# Colour per side
COLOURS = {
    "enemy":    (255,  80,  80),   # red
    "friendly": ( 80, 200,  80),   # green
    "tower":    (255, 200,   0),   # yellow (towers)
    "other":    (150, 150, 255),   # blue-grey
}

TOWER_CLASSES = {"king-tower", "queen-tower", "cannoneer-tower", "dagger-duchess-tower"}
BRIDGE_Y = 994   # approximate — update after calibration


def classify_side(cy: int) -> str:
    if cy < BRIDGE_Y:
        return "enemy"
    return "friendly"


def draw_clean(image: Image.Image, all_boxes: list, conf_thresh: float) -> Image.Image:
    """Draw only troop/building boxes with big readable labels."""
    draw = ImageDraw.Draw(image)

    for cls_name, conf, x1, y1, x2, y2 in all_boxes:
        if cls_name in UI_CLASSES:
            continue
        if conf < conf_thresh:
            continue

        cy = (y1 + y2) // 2
        side = "tower" if cls_name in TOWER_CLASSES else classify_side(cy)
        colour = COLOURS[side]

        # Draw thick bounding box
        for t in range(3):
            draw.rectangle([x1-t, y1-t, x2+t, y2+t], outline=colour)

        # Label background + text
        label = f"{cls_name} {conf:.0%}"
        font_size = 28
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((x1, y1 - font_size - 4), label, font=font)
        draw.rectangle(bbox, fill=colour)
        draw.text((x1, y1 - font_size - 4), label, fill=(0, 0, 0), font=font)

    return image


def run(screenshots_dir: str, out_dir: str, conf: float):
    screenshots = sorted(Path(screenshots_dir).glob("*.png"))
    if not screenshots:
        print(f"No screenshots found in {screenshots_dir}")
        return

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    summary_path = out_path / "summary.txt"

    print(f"Loading models...")
    m1 = YOLO("models/katacr/detector1_v0.7.13.pt")
    m2 = YOLO("models/katacr/detector2_v0.7.13.pt")
    print(f"Models ready. Processing {len(screenshots)} screenshots...\n")

    lines = []

    # Arena crop params for 1080x2400 (KataCR part2_2.22)
    ARENA_CROP = (0.020, 0.070, 0.960, 0.690)  # x%, y%, w%, h%
    YOLO_SIZE = (576, 896)

    for img_path in screenshots:
        img = Image.open(img_path).convert("RGB")
        iw, ih = img.size

        # Crop to arena region (matches training pipeline)
        ax1 = round(ARENA_CROP[0] * iw)
        ay1 = round(ARENA_CROP[1] * ih)
        ax2 = round((ARENA_CROP[0] + ARENA_CROP[2]) * iw)
        ay2 = round((ARENA_CROP[1] + ARENA_CROP[3]) * ih)
        arena = img.crop((ax1, ay1, ax2, ay2)).resize(YOLO_SIZE, Image.LANCZOS)
        sx = (ax2 - ax1) / YOLO_SIZE[0]
        sy = (ay2 - ay1) / YOLO_SIZE[1]

        # Collect all boxes from both detectors
        all_boxes = []
        seen_centers = []

        for model in [m1, m2]:
            results = model.predict(source=arena, conf=conf, iou=0.45, verbose=False)
            for box in results[0].boxes:
                cls_name = model.names[int(box.cls[0])]
                box_conf = float(box.conf[0])
                # Translate from crop coords → full-screen coords
                cx1, cy1, cx2, cy2 = box.xyxy[0].tolist()
                x1 = int(cx1 * sx) + ax1
                y1 = int(cy1 * sy) + ay1
                x2 = int(cx2 * sx) + ax1
                y2 = int(cy2 * sy) + ay1
                cx, cy = (x1+x2)//2, (y1+y2)//2

                # Skip duplicates (same center ±30px)
                if any(abs(cx-sc[0]) < 30 and abs(cy-sc[1]) < 30 for sc in seen_centers):
                    continue
                seen_centers.append((cx, cy))
                all_boxes.append((cls_name, box_conf, x1, y1, x2, y2))

        # Build text summary for this image
        troops = [(c, f, x1, y1, x2, y2) for (c, f, x1, y1, x2, y2) in all_boxes
                  if c not in UI_CLASSES and f >= conf]
        ui    = [(c, f, x1, y1, x2, y2) for (c, f, x1, y1, x2, y2) in all_boxes
                  if c in UI_CLASSES and f >= conf]

        header = f"\n{'='*60}\n{img_path.name}\n{'='*60}"
        lines.append(header)
        print(header)

        if troops:
            lines.append(f"TROOPS/BUILDINGS ({len(troops)}):")
            print(f"TROOPS/BUILDINGS ({len(troops)}):")
            for cls_name, box_conf, x1, y1, x2, y2 in sorted(troops, key=lambda t: -t[1]):
                cy = (y1+y2)//2
                side = "tower" if cls_name in TOWER_CLASSES else classify_side(cy)
                entry = f"  [{side:8s}] {cls_name:30s} conf={box_conf:.0%}  center=({(x1+x2)//2}, {cy})"
                lines.append(entry)
                print(entry)
        else:
            lines.append("  (no troop detections above threshold)")
            print("  (no troop detections above threshold)")

        lines.append(f"\nUI elements filtered out: {len(ui)}")
        print(f"UI elements filtered out: {len(ui)}")

        # Save annotated image
        annotated = draw_clean(img.copy(), all_boxes, conf)
        save_name = f"clean_{img_path.name}"
        annotated.save(out_path / save_name)
        print(f"Saved: {out_path / save_name}")

    # Write summary file
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"Summary written to: {summary_path}")
    print(f"Annotated images in: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", default="data/screenshots")
    parser.add_argument("--out", default="data/results/clean")
    parser.add_argument("--conf", type=float, default=0.35)
    args = parser.parse_args()
    run(args.screenshots, args.out, args.conf)
