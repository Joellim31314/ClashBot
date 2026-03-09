"""Integration test — verify the full pipeline connects."""
import pytest
from unittest.mock import MagicMock
from PIL import Image

from bot.screen import ScreenCapture
from bot.actions import ActionExecutor
from bot.state import GameStateDetector, GameState
from bot.strategy import RandomStrategy, Action


class TestPipelineIntegration:
    def test_full_pipeline_capture_to_action(self):
        test_img = Image.new("RGB", (720, 1280), color=(0, 0, 0))
        mock_screen = MagicMock(spec=ScreenCapture)
        mock_screen.capture.return_value = test_img

        detector = GameStateDetector(mock_screen)
        state = detector.detect(test_img)
        assert isinstance(state, GameState)

        strategy = RandomStrategy()
        action = strategy.decide(elixir=10)
        assert isinstance(action, Action)

        mock_executor = MagicMock(spec=ActionExecutor)
        mock_executor.play_card(action.slot, action.x, action.y)
        mock_executor.play_card.assert_called_once_with(action.slot, action.x, action.y)

    def test_strategy_returns_none_on_low_elixir(self):
        assert RandomStrategy().decide(elixir=3) is None

    def test_capture_and_detect_wires_correctly(self):
        test_img = Image.new("RGB", (720, 1280), color=(0, 0, 0))
        mock_screen = MagicMock()
        mock_screen.capture.return_value = test_img

        detector = GameStateDetector(mock_screen)
        state, image = detector.capture_and_detect()

        assert isinstance(state, GameState)
        assert image is test_img
        mock_screen.capture.assert_called_once()
