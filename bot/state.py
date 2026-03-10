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
    CHEST = "chest"
    TROPHY_ROAD = "trophy_road"


class GameStateDetector:
    """Detects game state purely from pixel indicators — no timers."""

    def __init__(self, screen_capture):
        self._screen = screen_capture

    @staticmethod
    def _pixel_in_range(pixel: tuple, color_min: tuple, color_max: tuple) -> bool:
        return all(lo <= val <= hi for val, lo, hi in zip(pixel, color_min, color_max))

    def _sample_pixel(self, pixels: np.ndarray, pos: tuple) -> tuple | None:
        """Return the RGB tuple at (x, y) or None if out of bounds."""
        x, y = pos
        if y >= pixels.shape[0] or x >= pixels.shape[1]:
            return None
        return tuple(pixels[y, x])

    # --- Per-state pixel checks ---

    def _is_battle_frame(self, pixels: np.ndarray) -> bool:
        pixel = self._sample_pixel(pixels, config.BATTLE_INDICATOR_POS)
        if pixel is None:
            return False
        return self._pixel_in_range(
            pixel,
            config.BATTLE_INDICATOR_COLOR_MIN,
            config.BATTLE_INDICATOR_COLOR_MAX,
        )

    def _is_chest_frame(self, pixels: np.ndarray) -> bool:
        pixel = self._sample_pixel(pixels, config.CHEST_INDICATOR_POS)
        if pixel is None:
            return False
        return self._pixel_in_range(
            pixel,
            config.CHEST_INDICATOR_COLOR_MIN,
            config.CHEST_INDICATOR_COLOR_MAX,
        )

    def _is_trophy_road_frame(self, pixels: np.ndarray) -> bool:
        pixel = self._sample_pixel(pixels, config.TROPHY_ROAD_INDICATOR_POS)
        if pixel is None:
            return False
        return self._pixel_in_range(
            pixel,
            config.TROPHY_ROAD_INDICATOR_COLOR_MIN,
            config.TROPHY_ROAD_INDICATOR_COLOR_MAX,
        )

    def _is_game_over_frame(self, pixels: np.ndarray) -> bool:
        pixel = self._sample_pixel(pixels, config.GAME_OVER_INDICATOR_POS)
        if pixel is None:
            return False
        return self._pixel_in_range(
            pixel,
            config.GAME_OVER_INDICATOR_COLOR_MIN,
            config.GAME_OVER_INDICATOR_COLOR_MAX,
        )

    def _is_menu_frame(self, pixels: np.ndarray) -> bool:
        pixel = self._sample_pixel(pixels, config.MENU_INDICATOR_POS)
        if pixel is None:
            return False
        return self._pixel_in_range(
            pixel,
            config.MENU_INDICATOR_COLOR_MIN,
            config.MENU_INDICATOR_COLOR_MAX,
        )

    # --- Debug helper ---

    def _log_all_indicator_pixels(self, pixels: np.ndarray):
        """Log the pixel values at every indicator position (for calibration)."""
        indicators = {
            "BATTLE":      config.BATTLE_INDICATOR_POS,
            "CHEST":       config.CHEST_INDICATOR_POS,
            "TROPHY_ROAD": config.TROPHY_ROAD_INDICATOR_POS,
            "GAME_OVER":   config.GAME_OVER_INDICATOR_POS,
            "MENU":        config.MENU_INDICATOR_POS,
        }
        parts = []
        for name, pos in indicators.items():
            px = self._sample_pixel(pixels, pos)
            parts.append(f"{name}{pos}={px}")
        logger.info("Indicator pixels — %s", "  |  ".join(parts))

    # --- Elixir ---

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

    # --- Main detection ---

    def detect(self, image: Image.Image) -> GameState:
        pixels = np.array(image)

        # Optional: dump every indicator pixel for calibration.
        if getattr(config, "DEBUG_STATE_PIXELS", False):
            self._log_all_indicator_pixels(pixels)

        # Priority order: BATTLE > CHEST > TROPHY_ROAD > GAME_OVER > MENU > UNKNOWN
        if self._is_battle_frame(pixels):
            return GameState.BATTLE

        if self._is_chest_frame(pixels):
            return GameState.CHEST

        if self._is_trophy_road_frame(pixels):
            return GameState.TROPHY_ROAD

        if self._is_game_over_frame(pixels):
            return GameState.GAME_OVER

        if self._is_menu_frame(pixels):
            return GameState.MENU

        return GameState.UNKNOWN

    def capture_and_detect(self) -> tuple[GameState, Image.Image]:
        image = self._screen.capture()
        state = self.detect(image)
        return state, image
