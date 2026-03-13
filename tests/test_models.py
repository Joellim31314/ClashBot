"""Tests for bot.models — shared data structures."""
import pytest

from bot.models import Detection, CardInHand, BattleScene, Action


class TestDetection:
    def test_has_required_fields(self):
        d = Detection(
            class_name="knight",
            confidence=0.95,
            bbox=(100, 200, 150, 280),
            center=(125, 240),
            side="friendly",
        )
        assert d.class_name == "knight"
        assert d.confidence == 0.95
        assert d.bbox == (100, 200, 150, 280)
        assert d.center == (125, 240)
        assert d.side == "friendly"


class TestCardInHand:
    def test_has_required_fields(self):
        c = CardInHand(slot=0, card_name="hog_rider", confidence=0.88)
        assert c.slot == 0
        assert c.card_name == "hog_rider"
        assert c.confidence == 0.88


class TestBattleScene:
    def test_defaults(self):
        scene = BattleScene()
        assert scene.detections == []
        assert scene.cards_in_hand == []
        assert scene.elixir == 0
        assert scene.timestamp == 0.0

    def test_with_data(self):
        det = Detection("knight", 0.9, (10, 20, 30, 40), (20, 30), "friendly")
        card = CardInHand(0, "knight", 0.85)
        scene = BattleScene(
            detections=[det],
            cards_in_hand=[card],
            elixir=7,
            timestamp=123.0,
        )
        assert len(scene.detections) == 1
        assert len(scene.cards_in_hand) == 1
        assert scene.elixir == 7

    def test_default_lists_are_independent(self):
        s1 = BattleScene()
        s2 = BattleScene()
        s1.detections.append(Detection("x", 0.5, (0, 0, 1, 1), (0, 0), "unknown"))
        assert len(s2.detections) == 0


class TestAction:
    def test_has_required_fields(self):
        action = Action(slot=2, x=360, y=530)
        assert action.slot == 2
        assert action.x == 360
        assert action.y == 530
