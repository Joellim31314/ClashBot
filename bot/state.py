"""Pixel-based game state detection for ClashBot."""
import logging
from enum import Enum

import numpy as np
from PIL import Image

import config

logger = logging.getLogger(__name__)


class GameState(Enum):
    UNKNOWN = "unknown"
    MENU = "menu"
    BATTLE = "battle"
    GAME_OVER = "game_over"


class GameStateDetector:
    def __init__(self, screen_capture):
        self._screen = screen_capture

    def _pixel_in_range(self, pixel: tuple, color_min: tuple, color_max: tuple) -> bool:
        return all(lo <= val <= hi for val, lo, hi in zip(pixel, color_min, color_max))

    def get_elixir_count(self, image: Image.Image) -> int:
        pixels = np.array(image)
        y = config.ELIXIR_BAR_Y
        x_start = config.ELIXIR_BAR_X_START
        x_end = config.ELIXIR_BAR_X_END
        pip_width = (x_end - x_start) / config.ELIXIR_PIP_COUNT
        filled = 0

        for i in range(config.ELIXIR_PIP_COUNT):
            x = int(x_start + pip_width * i + pip_width / 2)
            if y >= pixels.shape[0] or x >= pixels.shape[1]:
                continue
            pixel = tuple(pixels[y, x])
            if self._pixel_in_range(pixel, config.ELIXIR_FILLED_COLOR_MIN, config.ELIXIR_FILLED_COLOR_MAX):
                filled += 1

        logger.debug("Elixir count: %d", filled)
        return filled

    def detect(self, image: Image.Image) -> GameState:
        pixels = np.array(image)
        bx, by = config.BATTLE_INDICATOR_POS
        if by < pixels.shape[0] and bx < pixels.shape[1]:
            battle_pixel = tuple(pixels[by, bx])
            if self._pixel_in_range(battle_pixel, config.BATTLE_INDICATOR_COLOR_MIN, config.BATTLE_INDICATOR_COLOR_MAX):
                return GameState.BATTLE
        return GameState.MENU

    def capture_and_detect(self) -> tuple[GameState, Image.Image]:
        image = self._screen.capture()
        state = self.detect(image)
        return state, image
