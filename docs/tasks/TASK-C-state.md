# Task C: Game State Detection Module

> **Context:** Read `CLAUDE.md` and `config.py` first. Do NOT modify `config.py`.

## Your Job
Create `bot/state.py` and `tests/test_state.py`. Nothing else.

## Files You Own
- **Create:** `bot/state.py`
- **Create:** `tests/test_state.py`
- **Read only:** `config.py` (import from it, never edit)

## DO NOT TOUCH
- `bot/screen.py`, `bot/actions.py`, `bot/strategy.py`, `main.py` — other agents handle these

## What To Build

`GameState` enum and `GameStateDetector` class:

1. `GameState` enum: `UNKNOWN`, `MENU`, `BATTLE`, `GAME_OVER`
2. `GameStateDetector(screen_capture)` — takes any object with a `.capture()` method (duck-typed, do NOT import ScreenCapture)
3. `get_elixir_count(image) -> int` — samples pixels along the elixir bar at `config.ELIXIR_BAR_Y`, checks purple color range, returns 0-10
4. `detect(image) -> GameState` — checks pixel at `config.BATTLE_INDICATOR_POS` against color range
5. `capture_and_detect() -> tuple[GameState, Image]` — calls `self._screen.capture()` then `self.detect()`

### Implementation

```python
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
```

### Tests

```python
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
```

## Verify

```bash
pytest tests/test_state.py -v
```

All 6 tests should PASS.

## Commit

```bash
git add bot/state.py tests/test_state.py
git commit -m "feat: pixel-based game state detection (elixir, battle/menu)"
```
