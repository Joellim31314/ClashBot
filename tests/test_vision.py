"""Tests for bot.vision — YOLO detector and card template matcher."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from bot.vision import YOLODetector, CardMatcher
from bot.models import Detection, CardInHand
import config


class TestYOLODetector:
    def test_disabled_when_model_not_found(self):
        detector = YOLODetector(model_path="nonexistent/path.pt")
        assert not detector.is_loaded
        assert detector.detect(Image.new("RGB", (720, 1280))) == []

    def test_returns_empty_when_not_loaded(self):
        detector = YOLODetector(model_path="nonexistent.pt")
        result = detector.detect(Image.new("RGB", (720, 1280)))
        assert result == []
        assert isinstance(result, list)

    @patch("bot.vision.YOLO", create=True)
    def test_detect_parses_boxes(self, mock_yolo_cls, tmp_path):
        # Create a fake model file so the path check passes
        model_file = tmp_path / "test.pt"
        model_file.write_text("fake")

        # Mock YOLO model
        mock_model = MagicMock()
        mock_model.names = {0: "knight", 1: "archer"}

        # Mock detection result
        mock_box = MagicMock()
        mock_box.cls = [MagicMock(__getitem__=lambda s, i: 0)]
        mock_box.cls[0] = 0
        mock_box.conf = [MagicMock(__getitem__=lambda s, i: 0.92)]
        mock_box.conf[0] = 0.92
        mock_box.xyxy = [MagicMock(tolist=lambda: [100.0, 200.0, 150.0, 280.0])]

        mock_result = MagicMock()
        mock_result.boxes = [mock_box]
        mock_model.predict.return_value = [mock_result]

        mock_yolo_cls.return_value = mock_model

        with patch("bot.vision.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            # Need to reimport to get the patched version
            detector = YOLODetector.__new__(YOLODetector)
            detector._model = mock_model

        img = Image.new("RGB", (720, 1280))
        detections = detector.detect(img)

        assert len(detections) == 1
        assert detections[0].class_name == "knight"
        assert detections[0].confidence == 0.92
        assert detections[0].bbox == (100, 200, 150, 280)
        assert detections[0].center == (125, 240)


class TestCardMatcher:
    def test_disabled_when_dir_not_found(self):
        matcher = CardMatcher(template_dir="nonexistent/dir")
        assert not matcher.is_loaded

    def test_returns_unknown_when_no_templates(self):
        matcher = CardMatcher(template_dir="nonexistent/dir")
        img = Image.new("RGB", (720, 1280))
        cards = matcher.identify_hand(img)
        assert len(cards) == 4
        assert all(c.card_name == "unknown" for c in cards)
        assert all(c.confidence == 0.0 for c in cards)

    def test_loads_templates_from_dir(self, tmp_path):
        # Create fake template PNGs
        for name in ["knight", "archer"]:
            img = np.zeros((100, 80), dtype=np.uint8)
            cv2.imwrite(str(tmp_path / f"{name}.png"), img)

        matcher = CardMatcher(template_dir=str(tmp_path))
        assert matcher.is_loaded
        assert len(matcher._templates) == 2
        assert "knight" in matcher._templates
        assert "archer" in matcher._templates

    def test_identify_hand_returns_4_cards(self, tmp_path):
        # Create a template
        template = np.random.randint(0, 255, (100, 80), dtype=np.uint8)
        cv2.imwrite(str(tmp_path / "knight.png"), template)

        matcher = CardMatcher(template_dir=str(tmp_path))
        img = Image.new("RGB", (720, 1280), color=(128, 128, 128))
        cards = matcher.identify_hand(img)

        assert len(cards) == 4
        assert all(isinstance(c, CardInHand) for c in cards)
        assert [c.slot for c in cards] == [0, 1, 2, 3]

    def test_crop_card_slot_dimensions(self, tmp_path):
        # Create a dummy template so matcher is "loaded"
        cv2.imwrite(str(tmp_path / "test.png"), np.zeros((100, 80), dtype=np.uint8))
        matcher = CardMatcher(template_dir=str(tmp_path))

        img = Image.new("RGB", (720, 1280))
        crop = matcher._crop_card_slot(img, 0)

        assert crop.shape == (config.CARD_CROP_HEIGHT, config.CARD_CROP_WIDTH)
