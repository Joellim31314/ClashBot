"""Test KataCR pre-trained YOLO model on emulator screenshots.

Usage:
    python data/test_pretrained.py [--model PATH] [--screenshots DIR] [--save-dir DIR]

Downloads:
    Get KataCR detector weights from https://github.com/wty-yy/KataCR
    Save to models/katacr/
"""
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path so we can import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_model(model_path: str):
    """Load a YOLO model from the given path."""
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    path = Path(model_path)
    if not path.exists():
        logger.error("Model not found at %s", path)
        logger.info("Download KataCR weights from https://github.com/wty-yy/KataCR")
        logger.info("Save to models/katacr/detector.pt")
        sys.exit(1)

    logger.info("Loading model from %s", path)
    model = YOLO(str(path))
    logger.info("Model loaded. Classes: %s", len(model.names))
    return model


def run_inference(model, image_path: str, conf: float = 0.40, iou: float = 0.45):
    """Run YOLO inference on a single image."""
    img = Image.open(image_path).convert("RGB")
    logger.info("Running inference on %s (%dx%d)", image_path, img.width, img.height)

    results = model.predict(source=img, conf=conf, iou=iou, verbose=False)
    result = results[0]

    detections = []
    for box in result.boxes:
        cls_id = int(box.cls[0])
        cls_name = model.names[cls_id]
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        detections.append({
            "class": cls_name,
            "confidence": confidence,
            "bbox": (x1, y1, x2, y2),
            "center": (cx, cy),
        })

    logger.info("Found %d detections", len(detections))
    for d in detections:
        logger.info("  %s (%.2f) at %s", d["class"], d["confidence"], d["bbox"])

    return detections, result


def save_annotated(result, save_path: str):
    """Save the annotated image with bounding boxes."""
    annotated = result.plot()  # Returns BGR numpy array
    cv2.imwrite(save_path, annotated)
    logger.info("Saved annotated image to %s", save_path)


def main():
    parser = argparse.ArgumentParser(description="Test KataCR pre-trained YOLO model")
    parser.add_argument("--model", type=str, default="models/katacr/detector.pt",
                        help="Path to YOLO model weights")
    parser.add_argument("--screenshots", type=str, default="data/screenshots",
                        help="Directory containing test screenshots")
    parser.add_argument("--save-dir", type=str, default="data/results",
                        help="Directory to save annotated results")
    parser.add_argument("--conf", type=float, default=0.40,
                        help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45,
                        help="IOU threshold for NMS")
    args = parser.parse_args()

    model = load_model(args.model)

    screenshots_dir = Path(args.screenshots)
    if not screenshots_dir.exists():
        logger.error("Screenshots directory not found: %s", screenshots_dir)
        logger.info("Capture some battle screenshots first:")
        logger.info("  1. Start a battle in LDPlayer")
        logger.info("  2. Take screenshots with: adb exec-out screencap -p > data/screenshots/battle_01.png")
        sys.exit(1)

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted(
        p for p in screenshots_dir.iterdir()
        if p.suffix.lower() in (".png", ".jpg", ".jpeg")
    )

    if not image_files:
        logger.error("No images found in %s", screenshots_dir)
        sys.exit(1)

    logger.info("Testing %d screenshots...", len(image_files))
    total_detections = 0

    for img_path in image_files:
        detections, result = run_inference(model, str(img_path), args.conf, args.iou)
        total_detections += len(detections)

        save_path = str(save_dir / f"annotated_{img_path.name}")
        save_annotated(result, save_path)

    logger.info("=" * 60)
    logger.info("Summary: %d images, %d total detections (avg %.1f/image)",
                len(image_files), total_detections,
                total_detections / len(image_files) if image_files else 0)
    logger.info("Annotated results saved to %s", save_dir)

    if total_detections == 0:
        logger.warning("No detections found! The model may not work for our screenshots.")
        logger.warning("Consider: fine-tuning (Task 3) or adjusting confidence threshold.")
    elif total_detections / len(image_files) < 3:
        logger.warning("Low detection count. Consider fine-tuning for better results.")
    else:
        logger.info("Model looks promising! Proceed with integration (Task 5).")


if __name__ == "__main__":
    main()
