"""Integration test — verify the full pipeline connects."""
import pytest
from unittest.mock import MagicMock
from PIL import Image

from bot.screen import ScreenCapture
from bot.actions import ActionExecutor
from bot.state import GameStateDetector, GameState
from bot.strategy import RandomStrategy
from bot.models import Action, BattleScene


class TestPipelineIntegration:
    def test_full_pipeline_capture_to_action(self):
        test_img = Image.new("RGB", (720, 1280), color=(0, 0, 0))
        mock_screen = MagicMock(spec=ScreenCapture)
        mock_screen.capture.return_value = test_img

        detector = GameStateDetector(mock_screen)
        state = detector.detect(test_img)
        assert isinstance(state, GameState)

        strategy = RandomStrategy()
        scene = BattleScene(elixir=10)
        action = strategy.decide(scene)
        assert isinstance(action, Action)

        mock_executor = MagicMock(spec=ActionExecutor)
        mock_executor.play_card(action.slot, action.x, action.y)
        mock_executor.play_card.assert_called_once_with(action.slot, action.x, action.y)

    def test_strategy_returns_none_on_low_elixir(self):
        assert RandomStrategy().decide(BattleScene(elixir=3)) is None

    def test_capture_and_detect_wires_correctly(self):
        test_img = Image.new("RGB", (720, 1280), color=(0, 0, 0))
        mock_screen = MagicMock()
        mock_screen.capture.return_value = test_img

        detector = GameStateDetector(mock_screen)
        state, image = detector.capture_and_detect()

        assert isinstance(state, GameState)
        assert image is test_img
        mock_screen.capture.assert_called_once()

    def test_get_battle_scene_without_vision(self):
        """Pipeline works without YOLO/card matcher (Phase 1 fallback)."""
        test_img = Image.new("RGB", (720, 1280), color=(0, 0, 0))
        mock_screen = MagicMock(spec=ScreenCapture)
        mock_screen.capture.return_value = test_img

        detector = GameStateDetector(mock_screen)  # No vision modules
        scene = detector.get_battle_scene(test_img)

        assert isinstance(scene, BattleScene)
        assert scene.detections == []
        assert scene.cards_in_hand == []
        assert scene.elixir == 0  # Black image = no elixir pips lit

    def test_full_pipeline_with_battle_scene(self):
        """Full pipeline: capture → detect state → build scene → decide action."""
        test_img = Image.new("RGB", (720, 1280), color=(0, 0, 0))
        mock_screen = MagicMock(spec=ScreenCapture)
        mock_screen.capture.return_value = test_img

        detector = GameStateDetector(mock_screen)
        scene = detector.get_battle_scene(test_img)
        scene.elixir = 10  # Override to trigger action

        strategy = RandomStrategy()
        action = strategy.decide(scene)
        assert isinstance(action, Action)
        assert 0 <= action.slot <= 3
