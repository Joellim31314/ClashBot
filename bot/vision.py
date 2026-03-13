"""YOLO object detection and card template matching for ClashBot."""
import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import config
from bot.models import Detection, CardInHand

logger = logging.getLogger(__name__)


class YOLODetector:
    """Detects arena troops and buildings using a YOLO model."""

    def __init__(self, model_path: str | None = None):
        self._model = None
        path = model_path or config.YOLO_MODEL_PATH

        try:
            from ultralytics import YOLO
            if not Path(path).exists():
                logger.warning("YOLO model not found at %s — detector disabled", path)
                return
            self._model = YOLO(path)
            logger.info("YOLO model loaded from %s (%d classes)",
                        path, len(self._model.names))
        except ImportError:
            logger.warning("ultralytics not installed — YOLO detector disabled")
        except Exception:
            logger.exception("Failed to load YOLO model from %s", path)

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def detect(self, image: Image.Image) -> list[Detection]:
        """Run YOLO inference on a screenshot, return list of Detections."""
        if not self.is_loaded:
            return []

        results = self._model.predict(
            source=image,
            conf=config.YOLO_CONFIDENCE_THRESHOLD,
            iou=config.YOLO_IOU_THRESHOLD,
            verbose=False,
        )
        result = results[0]

        detections = []
        for box in result.boxes:
            cls_id = int(box.cls[0])
            cls_name = self._model.names[cls_id]
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Classify side based on y-position relative to bridge
            if cy < config.ARENA_BRIDGE_Y:
                side = "enemy"
            elif cy > config.ARENA_BRIDGE_Y:
                side = "friendly"
            else:
                side = "unknown"

            detections.append(Detection(
                class_name=cls_name,
                confidence=confidence,
                bbox=(x1, y1, x2, y2),
                center=(cx, cy),
                side=side,
            ))

        logger.debug("YOLO detected %d objects", len(detections))
        return detections


class CardMatcher:
    """Identifies cards in hand using template matching."""

    def __init__(self, template_dir: str | None = None):
        self._templates: dict[str, np.ndarray] = {}
        tdir = Path(template_dir or config.CARD_TEMPLATE_DIR)

        if not tdir.exists():
            logger.warning("Card template directory not found: %s — matcher disabled", tdir)
            return

        for png in sorted(tdir.glob("*.png")):
            name = png.stem  # e.g. "knight" from "knight.png"
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
                # Resize template to match crop if needed
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
