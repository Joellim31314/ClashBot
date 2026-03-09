"""Tests for bot.state — pixel-based game state detection."""
import pytest
from unittest.mock import MagicMock
from PIL import Image
import numpy as np

from bot.state import GameStateDetector, GameState
import config


def make_solid_image(color: tuple) -> Image.Image:
    return Image.new("RGB", (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), color=color)


class TestGameStateEnum:
    def test_has_expected_states(self):
        assert GameState.UNKNOWN is not None
        assert GameState.MENU is not None
        assert GameState.BATTLE is not None
        assert GameState.GAME_OVER is not None


class TestElixirCount:
    def test_returns_0_for_black_elixir_bar(self):
        img = make_solid_image((0, 0, 0))
        detector = GameStateDetector(MagicMock())
        assert detector.get_elixir_count(img) == 0

    def test_returns_10_for_fully_purple_elixir_bar(self):
        img = make_solid_image((0, 0, 0))
        pixels = np.array(img)
        y = config.ELIXIR_BAR_Y
        pixels[y, config.ELIXIR_BAR_X_START:config.ELIXIR_BAR_X_END] = [200, 50, 200]
        img = Image.fromarray(pixels)

        detector = GameStateDetector(MagicMock())
        assert detector.get_elixir_count(img) == 10

    def test_returns_int_between_0_and_10(self):
        img = make_solid_image((100, 100, 100))
        detector = GameStateDetector(MagicMock())
        count = detector.get_elixir_count(img)
        assert isinstance(count, int)
        assert 0 <= count <= 10


class TestDetectState:
    def test_returns_game_state_enum(self):
        img = make_solid_image((100, 100, 100))
        detector = GameStateDetector(MagicMock())
        state = detector.detect(img)
        assert isinstance(state, GameState)

    def test_detects_battle_from_indicator_pixel(self):
        img = make_solid_image((0, 0, 0))
        pixels = np.array(img)
        bx, by = config.BATTLE_INDICATOR_POS
        pixels[by, bx] = [100, 100, 200]  # Within battle indicator range
        img = Image.fromarray(pixels)

        detector = GameStateDetector(MagicMock())
        assert detector.detect(img) == GameState.BATTLE
