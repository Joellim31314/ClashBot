"""YOLO object detection and card template matching for ClashBot."""
import logging
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import config
from bot.models import Detection, CardInHand

logger = logging.getLogger(__name__)

# KataCR class names that are UI/background elements, not troops/buildings
_UI_CLASSES = frozenset({
    "tower-bar", "bar", "bar-level", "elixir", "emote", "clock",
    "padding_belong", "evolution-symbol", "ice-spirit-evolution-symbol",
    "skeleton-king-bar", "selected", "text", "king-tower-bar",
    "dagger-duchess-tower-bar",
})

# Path to vendor KataCR repo (needed for custom model classes)
_KATACR_VENDOR_PATH = str(Path(__file__).resolve().parent.parent / "vendor" / "KataCR")

# KataCR arena crop for 1080x2400 (ratio 2.22): 'part2_2.22': (x%, y%, w%, h%)
# Crops the battle arena before feeding to YOLO — the model was trained on this crop.
# All detection coordinates are in crop space; we translate back to full-screen below.
_ARENA_CROP = (0.020, 0.070, 0.960, 0.690)   # (x_frac, y_frac, w_frac, h_frac)
_YOLO_INPUT_SIZE = (576, 896)                  # (width, height) the model was trained on


def _get_arena_crop_box(img_w: int, img_h: int) -> tuple[int, int, int, int]:
    """Return (x1, y1, x2, y2) pixel coords of the arena crop for a given screen size."""
    xf, yf, wf, hf = _ARENA_CROP
    x1 = round(xf * img_w)
    y1 = round(yf * img_h)
    x2 = round((xf + wf) * img_w)
    y2 = round((yf + hf) * img_h)
    return x1, y1, x2, y2


def _patch_torch_load():
    """Patch torch.load for PyTorch 2.6+ compatibility with KataCR weights."""
    import torch
    if not getattr(torch, "_clashbot_patched", False):
        _original = torch.load
        def _patched(*args, **kwargs):
            kwargs.setdefault("weights_only", False)
            return _original(*args, **kwargs)
        torch.load = _patched
        torch._clashbot_patched = True


class YOLODetector:
    """Detects arena troops and buildings using KataCR's dual YOLO detectors."""

    def __init__(self, model_path: str | None = None):
        self._models: list = []
        self._filter_ui = True

        # Add KataCR vendor path for custom model classes
        if _KATACR_VENDOR_PATH not in sys.path and Path(_KATACR_VENDOR_PATH).exists():
            sys.path.insert(0, _KATACR_VENDOR_PATH)

        try:
            _patch_torch_load()
            from ultralytics import YOLO

            if model_path:
                # Single model mode (custom path)
                if not Path(model_path).exists():
                    logger.warning("YOLO model not found at %s — detector disabled", model_path)
                    return
                self._models = [YOLO(model_path)]
                logger.info("YOLO model loaded from %s (%d classes)",
                            model_path, len(self._models[0].names))
            else:
                # Dual-detector mode: try KataCR detectors first, fall back to single model
                katacr_dir = Path("models/katacr")
                det1 = katacr_dir / "detector1_v0.7.13.pt"
                det2 = katacr_dir / "detector2_v0.7.13.pt"

                if det1.exists() and det2.exists():
                    self._models = [YOLO(str(det1)), YOLO(str(det2))]
                    logger.info("KataCR dual detectors loaded (det1: %d cls, det2: %d cls)",
                                len(self._models[0].names), len(self._models[1].names))
                elif Path(config.YOLO_MODEL_PATH).exists():
                    self._models = [YOLO(config.YOLO_MODEL_PATH)]
                    logger.info("Single YOLO model loaded from %s", config.YOLO_MODEL_PATH)
                else:
                    logger.warning("No YOLO models found — detector disabled")

        except ImportError:
            logger.warning("ultralytics not installed — YOLO detector disabled")
        except Exception:
            logger.exception("Failed to load YOLO model(s)")

    @property
    def is_loaded(self) -> bool:
        return len(self._models) > 0

    def detect(self, image: Image.Image) -> list[Detection]:
        """Run YOLO inference on a screenshot, return list of Detections.

        Crops the arena region first (matching KataCR's training pipeline),
        then translates bounding boxes back to full-screen coordinates.
        """
        if not self.is_loaded:
            return []

        # Crop to arena region — model was trained on this crop, not the full screen
        img_w, img_h = image.size
        ax1, ay1, ax2, ay2 = _get_arena_crop_box(img_w, img_h)
        arena_crop = image.crop((ax1, ay1, ax2, ay2)).resize(
            _YOLO_INPUT_SIZE, Image.LANCZOS
        )

        # Scale factors to translate crop coords → full-screen coords
        crop_w = ax2 - ax1
        crop_h = ay2 - ay1
        sx = crop_w / _YOLO_INPUT_SIZE[0]
        sy = crop_h / _YOLO_INPUT_SIZE[1]

        all_detections = []
        seen_boxes: list[tuple[int, int, int, int]] = []

        for model in self._models:
            results = model.predict(
                source=arena_crop,
                conf=config.YOLO_CONFIDENCE_THRESHOLD,
                iou=config.YOLO_IOU_THRESHOLD,
                verbose=False,
            )
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]

                if self._filter_ui and cls_name in _UI_CLASSES:
                    continue

                confidence = float(box.conf[0])
                # Translate from crop coords → full-screen coords
                cx1, cy1, cx2, cy2 = box.xyxy[0].tolist()
                x1 = int(cx1 * sx) + ax1
                y1 = int(cy1 * sy) + ay1
                x2 = int(cx2 * sx) + ax1
                y2 = int(cy2 * sy) + ay1

                bbox = (x1, y1, x2, y2)
                if _is_duplicate(bbox, seen_boxes, iou_threshold=0.5):
                    continue
                seen_boxes.append(bbox)

                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                if cy < config.ARENA_BRIDGE_Y:
                    side = "enemy"
                elif cy > config.ARENA_BRIDGE_Y:
                    side = "friendly"
                else:
                    side = "unknown"

                all_detections.append(Detection(
                    class_name=cls_name,
                    confidence=confidence,
                    bbox=bbox,
                    center=(cx, cy),
                    side=side,
                ))

        logger.debug("YOLO detected %d objects (after filtering)", len(all_detections))
        return all_detections


def _iou(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> float:
    """Compute Intersection over Union between two boxes (x1, y1, x2, y2)."""
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _is_duplicate(bbox: tuple[int, int, int, int],
                  seen: list[tuple[int, int, int, int]],
                  iou_threshold: float = 0.5) -> bool:
    """Check if a bbox overlaps significantly with any already-seen box."""
    for existing in seen:
        if _iou(bbox, existing) > iou_threshold:
            return True
    return False


class CardMatcher:
    """Identifies cards in hand using template matching."""

    def __init__(self, template_dir: str | None = None):
        self._templates: dict[str, np.ndarray] = {}
        tdir = Path(template_dir or config.CARD_TEMPLATE_DIR)

        if not tdir.exists():
            logger.warning("Card template directory not found: %s — matcher disabled", tdir)
            return

        for png in sorted(tdir.glob("*.png")):
            name = png.stem
            img = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                self._templates[name] = img

        logger.info("Loaded %d card templates from %s", len(self._templates), tdir)

    @property
    def is_loaded(self) -> bool:
        return len(self._templates) > 0

    def _crop_card_slot(self, image: Image.Image, slot: int) -> np.ndarray:
        """Crop and convert a card slot region to grayscale numpy array."""
        cx = config.CARD_SLOT_X[slot]
        cy = config.CARD_SLOT_Y
        w = config.CARD_CROP_WIDTH
        h = config.CARD_CROP_HEIGHT
        y_off = config.CARD_CROP_Y_OFFSET

        left = cx - w // 2
        top = cy + y_off
        right = left + w
        bottom = top + h

        crop = image.crop((left, top, right, bottom))
        return cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2GRAY)

    def identify_hand(self, image: Image.Image) -> list[CardInHand]:
        """Identify cards in all 4 hand slots using template matching."""
        if not self.is_loaded:
            return [CardInHand(slot=i, card_name="unknown", confidence=0.0) for i in range(4)]

        cards = []
        for slot in range(4):
            crop = self._crop_card_slot(image, slot)

            best_name = "unknown"
            best_score = 0.0

            for name, template in self._templates.items():
                if template.shape != crop.shape:
                    template_resized = cv2.resize(template, (crop.shape[1], crop.shape[0]))
                else:
                    template_resized = template

                result = cv2.matchTemplate(crop, template_resized, cv2.TM_CCOEFF_NORMED)
                score = float(result.max())

                if score > best_score:
                    best_score = score
                    best_name = name

            if best_score < config.CARD_MATCH_THRESHOLD:
                best_name = "unknown"

            cards.append(CardInHand(slot=slot, card_name=best_name, confidence=best_score))
            logger.debug("Slot %d: %s (%.2f)", slot, best_name, best_score)

        return cards
