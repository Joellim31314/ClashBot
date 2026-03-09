# Phase 1: Foundation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a working end-to-end pipeline: screen capture → state detection → random card play → action execution. The bot will lose every game, but the pipeline works.

**Architecture:** ADB connects to LDPlayer 9 emulator running Clash Royale at 720x1280. Python captures screenshots via ADB, analyzes pixels to detect game state (menu/battle/game-over, elixir count), picks a random card when elixir is sufficient, and taps the emulator to play it.

**Tech Stack:** Python 3.11+, pure-python-adb, Pillow, NumPy, OpenCV, pytest

---

## Prerequisites (Manual — User Must Complete)

Before ANY code task can be verified against the real emulator:

1. Install **LDPlayer 9** from [ldplayer.net](https://www.ldplayer.net/)
2. Set display resolution to **720x1280** in LDPlayer Settings → Display
3. Install **Clash Royale** from Play Store inside LDPlayer
4. Create a **throwaway Supercell account**, complete the tutorial
5. Enable **ADB**: LDPlayer Settings → Other → ADB debugging → Open local connection
6. Note the ADB port shown in LDPlayer (usually `5555` or `5557`)

---

## Dependency Graph

```
Task 1 (scaffolding) ──────┬──────────────────────────────────┐
                            │                                  │
                    ┌───────▼────────┐              ┌──────────▼──────────┐
                    │  Task 2         │              │  Task 3              │
                    │  screen.py      │              │  actions.py          │
                    │  (ADB capture)  │              │  (ADB tap/swipe)     │
                    └───────┬────────┘              └──────────┬──────────┘
                            │                                  │
                    ┌───────▼────────┐                         │
                    │  Task 4         │                         │
                    │  state.py       │                         │
                    │  (pixel detect) │                         │
                    └───────┬────────┘                         │
                            │                                  │
                    ┌───────▼──────────────────────────────────▼┐
                    │  Task 5                                    │
                    │  strategy.py (random card play)            │
                    └───────┬──────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Task 6         │
                    │  main.py        │
                    │  (game loop +   │
                    │   integration)  │
                    └────────────────┘
```

### Parallel Execution Guide

| Wave | Tasks | Can Run In Parallel? | Agents Needed |
|------|-------|---------------------|---------------|
| **Wave 1** | Task 1 (scaffolding) | Single task | 1 |
| **Wave 2** | Task 2 (screen.py) + Task 3 (actions.py) | **Yes — fully independent** | 2 |
| **Wave 3** | Task 4 (state.py) | Needs screen.py from Wave 2 | 1 |
| **Wave 4** | Task 5 (strategy.py) | Needs state.py from Wave 3 | 1 |
| **Wave 5** | Task 6 (main.py + integration) | Needs all above | 1 |

---

## Task 1: Project Scaffolding + Config

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `bot/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create `requirements.txt`**

```
pure-python-adb>=0.3.0
Pillow>=10.0.0
numpy>=1.24.0
opencv-python>=4.8.0
pytest>=7.4.0
```

**Step 2: Create `config.py`**

```python
"""
All hardcoded coordinates and constants for ClashBot.
Resolution: 720x1280 (LDPlayer 9).
Coordinate origin: top-left corner (0,0).

IMPORTANT: Every coordinate in this file is calibrated for 720x1280.
If the emulator resolution changes, ALL values must be recalibrated.
"""

# --- Emulator Connection ---
ADB_HOST = "127.0.0.1"
ADB_PORT = 5037  # ADB server port (not emulator port)
EMULATOR_SERIAL = "emulator-5554"  # LDPlayer default; adjust if needed

# --- Screen Dimensions ---
SCREEN_WIDTH = 720
SCREEN_HEIGHT = 1280

# --- Card Slots (bottom of screen, 4 card hand) ---
# Y coordinate for the center of card slots
CARD_SLOT_Y = 1190
# X coordinates for each of the 4 card slots (left to right)
CARD_SLOT_X = [120, 240, 360, 480]
# Next card (5th card, partially visible)
NEXT_CARD_X = 600
NEXT_CARD_Y = 1190

# --- Arena Play Zones ---
# Where cards can be placed (your side of the arena)
ARENA_LEFT_X = 80
ARENA_RIGHT_X = 640
ARENA_TOP_Y = 300      # Enemy side (top)
ARENA_BRIDGE_Y = 530   # Bridge line
ARENA_MID_Y = 700      # Center of your side
ARENA_BOTTOM_Y = 1000  # Near your towers

# Bridge positions (common placement spots)
LEFT_BRIDGE = (180, 530)
RIGHT_BRIDGE = (540, 530)

# --- Tower Positions ---
ENEMY_KING_TOWER = (360, 150)
ENEMY_LEFT_PRINCESS = (180, 250)
ENEMY_RIGHT_PRINCESS = (540, 250)
FRIENDLY_KING_TOWER = (360, 1050)
FRIENDLY_LEFT_PRINCESS = (180, 920)
FRIENDLY_RIGHT_PRINCESS = (540, 920)

# --- Elixir Bar ---
# The elixir bar is at the bottom of the screen
# Each elixir pip lights up from left to right
ELIXIR_BAR_Y = 1245
ELIXIR_BAR_X_START = 100
ELIXIR_BAR_X_END = 620
ELIXIR_PIP_COUNT = 10
# Color of a filled elixir pip (purple/pink)
ELIXIR_FILLED_COLOR_MIN = (150, 0, 150)  # RGB lower bound
ELIXIR_FILLED_COLOR_MAX = (255, 100, 255)  # RGB upper bound

# --- UI Buttons ---
BATTLE_BUTTON = (360, 950)       # Main menu "Battle" button
OK_BUTTON = (360, 1050)          # Post-game OK/Continue button
MENU_RETURN_BUTTON = (360, 1200) # Return to menu after game

# --- Game State Detection ---
# Pixel sample points and expected colors for detecting screen state
# These are (x, y, expected_color_range) tuples
# The battle screen has the arena visible
BATTLE_INDICATOR_POS = (360, 50)  # Top center — timer area during battle
BATTLE_INDICATOR_COLOR_MIN = (50, 50, 100)
BATTLE_INDICATOR_COLOR_MAX = (150, 150, 255)

# Menu screen has the Clash Royale logo area
MENU_INDICATOR_POS = (360, 200)   # Center area with menu elements

# --- Timing ---
CAPTURE_INTERVAL = 0.5     # Seconds between screen captures in main loop
ACTION_DELAY_MIN = 0.05    # Minimum delay between actions (seconds)
ACTION_DELAY_MAX = 0.20    # Maximum delay between actions (seconds)
POST_GAME_WAIT = 3.0       # Seconds to wait after game ends
ELIXIR_WAIT_THRESHOLD = 7  # Minimum elixir before playing a card (Phase 1)

# --- Logging ---
LOG_LEVEL = "INFO"
LOG_FILE = "clashbot.log"
```

**Step 3: Create `bot/__init__.py` and `tests/__init__.py`**

Both files are empty (just make them exist so Python treats directories as packages).

**Step 4: Set up virtual environment**

Run:
```bash
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
pip install -r requirements.txt
```

**Step 5: Commit**

```bash
git init
git add requirements.txt config.py bot/__init__.py tests/__init__.py
git commit -m "feat: project scaffolding with config and dependencies"
```

---

## Task 2: Screen Capture Module (Agent A)

**Files:**
- Create: `bot/screen.py`
- Create: `tests/test_screen.py`

**Depends on:** Task 1 (config.py must exist)

**Step 1: Write failing tests for `ScreenCapture`**

Create `tests/test_screen.py`:

```python
"""Tests for bot.screen — ADB screen capture module."""
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from bot.screen import ScreenCapture
import config


class TestScreenCaptureInit:
    """Test ScreenCapture initialization and connection."""

    @patch("bot.screen.AdbClient")
    def test_creates_adb_client_with_config(self, mock_adb_cls):
        mock_client = MagicMock()
        mock_client.devices.return_value = [MagicMock()]
        mock_adb_cls.return_value = mock_client

        sc = ScreenCapture()

        mock_adb_cls.assert_called_once_with(host=config.ADB_HOST, port=config.ADB_PORT)

    @patch("bot.screen.AdbClient")
    def test_is_connected_returns_true_when_device_found(self, mock_adb_cls):
        mock_device = MagicMock()
        mock_client = MagicMock()
        mock_client.devices.return_value = [mock_device]
        mock_adb_cls.return_value = mock_client

        sc = ScreenCapture()
        assert sc.is_connected() is True

    @patch("bot.screen.AdbClient")
    def test_is_connected_returns_false_when_no_devices(self, mock_adb_cls):
        mock_client = MagicMock()
        mock_client.devices.return_value = []
        mock_adb_cls.return_value = mock_client

        sc = ScreenCapture()
        assert sc.is_connected() is False


class TestScreenCapture:
    """Test screen capture functionality."""

    @patch("bot.screen.AdbClient")
    def test_capture_returns_pil_image(self, mock_adb_cls):
        # Create a small test PNG in memory
        test_img = Image.new("RGB", (720, 1280), color=(100, 100, 100))
        import io
        buf = io.BytesIO()
        test_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        mock_device = MagicMock()
        mock_device.shell.return_value = png_bytes
        mock_client = MagicMock()
        mock_client.devices.return_value = [mock_device]
        mock_adb_cls.return_value = mock_client

        sc = ScreenCapture()
        result = sc.capture()

        assert isinstance(result, Image.Image)
        assert result.size == (720, 1280)

    @patch("bot.screen.AdbClient")
    def test_capture_raises_when_not_connected(self, mock_adb_cls):
        mock_client = MagicMock()
        mock_client.devices.return_value = []
        mock_adb_cls.return_value = mock_client

        sc = ScreenCapture()
        with pytest.raises(ConnectionError):
            sc.capture()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_screen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.screen'`

**Step 3: Implement `bot/screen.py`**

```python
"""ADB screen capture module for ClashBot.

Connects to an Android emulator via ADB and captures screenshots
as PIL Images for downstream processing.
"""
import io
import logging
from PIL import Image
from ppadb.client import Client as AdbClient

import config

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Captures screenshots from the Android emulator via ADB."""

    def __init__(self):
        self._client = AdbClient(host=config.ADB_HOST, port=config.ADB_PORT)
        self._device = None
        self._connect()

    def _connect(self):
        """Find and connect to the first available ADB device."""
        devices = self._client.devices()
        if devices:
            self._device = devices[0]
            logger.info("Connected to device: %s", self._device.serial)
        else:
            logger.warning("No ADB devices found. Is the emulator running?")

    def is_connected(self) -> bool:
        """Check if an ADB device is connected."""
        return self._device is not None

    def capture(self) -> Image.Image:
        """Capture a screenshot from the emulator.

        Returns:
            PIL Image in RGB mode, resolution should be 720x1280.

        Raises:
            ConnectionError: If no device is connected.
        """
        if not self.is_connected():
            raise ConnectionError("No ADB device connected. Start the emulator first.")

        png_bytes = self._device.screencap()
        image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        logger.debug("Captured frame: %s", image.size)
        return image

    def reconnect(self):
        """Attempt to reconnect to the ADB device."""
        logger.info("Attempting ADB reconnection...")
        self._device = None
        self._connect()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_screen.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add bot/screen.py tests/test_screen.py
git commit -m "feat: ADB screen capture module with tests"
```

---

## Task 3: Action Executor Module (Agent B — parallel with Task 2)

**Files:**
- Create: `bot/actions.py`
- Create: `tests/test_actions.py`

**Depends on:** Task 1 (config.py must exist)

**Step 1: Write failing tests for `ActionExecutor`**

Create `tests/test_actions.py`:

```python
"""Tests for bot.actions — ADB action execution module."""
import pytest
from unittest.mock import MagicMock, patch, call
import time

from bot.actions import ActionExecutor
import config


class TestActionExecutorTap:
    """Test tap actions."""

    @patch("bot.actions.AdbClient")
    def test_tap_sends_correct_adb_command(self, mock_adb_cls):
        mock_device = MagicMock()
        mock_client = MagicMock()
        mock_client.devices.return_value = [mock_device]
        mock_adb_cls.return_value = mock_client

        executor = ActionExecutor()
        executor.tap(360, 640)

        mock_device.shell.assert_called_once_with("input tap 360 640")

    @patch("bot.actions.AdbClient")
    def test_tap_raises_when_not_connected(self, mock_adb_cls):
        mock_client = MagicMock()
        mock_client.devices.return_value = []
        mock_adb_cls.return_value = mock_client

        executor = ActionExecutor()
        with pytest.raises(ConnectionError):
            executor.tap(360, 640)


class TestActionExecutorPlayCard:
    """Test card playing actions."""

    @patch("bot.actions.time")
    @patch("bot.actions.AdbClient")
    def test_play_card_taps_card_slot_then_arena_position(self, mock_adb_cls, mock_time):
        mock_device = MagicMock()
        mock_client = MagicMock()
        mock_client.devices.return_value = [mock_device]
        mock_adb_cls.return_value = mock_client

        executor = ActionExecutor()
        executor.play_card(slot=0, x=180, y=530)

        calls = mock_device.shell.call_args_list
        # First call: tap the card slot
        assert calls[0] == call(f"input tap {config.CARD_SLOT_X[0]} {config.CARD_SLOT_Y}")
        # Second call: tap the arena position
        assert calls[1] == call("input tap 180 530")

    @patch("bot.actions.AdbClient")
    def test_play_card_validates_slot_range(self, mock_adb_cls):
        mock_device = MagicMock()
        mock_client = MagicMock()
        mock_client.devices.return_value = [mock_device]
        mock_adb_cls.return_value = mock_client

        executor = ActionExecutor()
        with pytest.raises(ValueError, match="slot"):
            executor.play_card(slot=5, x=180, y=530)


class TestActionExecutorSwipe:
    """Test swipe actions."""

    @patch("bot.actions.AdbClient")
    def test_swipe_sends_correct_adb_command(self, mock_adb_cls):
        mock_device = MagicMock()
        mock_client = MagicMock()
        mock_client.devices.return_value = [mock_device]
        mock_adb_cls.return_value = mock_client

        executor = ActionExecutor()
        executor.swipe(100, 200, 300, 400, duration_ms=300)

        mock_device.shell.assert_called_once_with("input swipe 100 200 300 400 300")
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_actions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.actions'`

**Step 3: Implement `bot/actions.py`**

```python
"""ADB action execution module for ClashBot.

Sends tap and swipe commands to the Android emulator via ADB
to control Clash Royale gameplay.
"""
import logging
import random
import time

from ppadb.client import Client as AdbClient

import config

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes game actions via ADB commands."""

    def __init__(self):
        self._client = AdbClient(host=config.ADB_HOST, port=config.ADB_PORT)
        self._device = None
        self._connect()

    def _connect(self):
        """Find and connect to the first available ADB device."""
        devices = self._client.devices()
        if devices:
            self._device = devices[0]
            logger.info("ActionExecutor connected to: %s", self._device.serial)
        else:
            logger.warning("No ADB devices found.")

    def is_connected(self) -> bool:
        """Check if an ADB device is connected."""
        return self._device is not None

    def _ensure_connected(self):
        if not self.is_connected():
            raise ConnectionError("No ADB device connected.")

    def _random_delay(self):
        """Add a small random delay to mimic human behavior."""
        delay = random.uniform(config.ACTION_DELAY_MIN, config.ACTION_DELAY_MAX)
        time.sleep(delay)

    def tap(self, x: int, y: int):
        """Tap a screen coordinate.

        Args:
            x: X coordinate (0-719 for 720 width)
            y: Y coordinate (0-1279 for 1280 height)
        """
        self._ensure_connected()
        self._device.shell(f"input tap {x} {y}")
        logger.debug("Tapped (%d, %d)", x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """Swipe from one point to another.

        Args:
            x1, y1: Start coordinates
            x2, y2: End coordinates
            duration_ms: Swipe duration in milliseconds
        """
        self._ensure_connected()
        self._device.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")
        logger.debug("Swiped (%d,%d) → (%d,%d)", x1, y1, x2, y2)

    def play_card(self, slot: int, x: int, y: int):
        """Play a card from hand to an arena position.

        Args:
            slot: Card slot index (0-3, left to right)
            x: Target X coordinate on the arena
            y: Target Y coordinate on the arena

        Raises:
            ValueError: If slot is not 0-3.
        """
        if slot < 0 or slot > 3:
            raise ValueError(f"Invalid slot {slot}: must be 0-3")

        self._ensure_connected()

        # Step 1: Tap the card in hand
        card_x = config.CARD_SLOT_X[slot]
        card_y = config.CARD_SLOT_Y
        self._device.shell(f"input tap {card_x} {card_y}")
        logger.debug("Selected card slot %d at (%d, %d)", slot, card_x, card_y)

        self._random_delay()

        # Step 2: Tap the arena position to place it
        self._device.shell(f"input tap {x} {y}")
        logger.info("Played card slot %d → (%d, %d)", slot, x, y)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_actions.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add bot/actions.py tests/test_actions.py
git commit -m "feat: ADB action executor with tap, swipe, and play_card"
```

---

## Task 4: Game State Detection Module

**Files:**
- Create: `bot/state.py`
- Create: `tests/test_state.py`

**Depends on:** Task 2 (screen.py — needs ScreenCapture for screenshots)

**Step 1: Write failing tests for `GameStateDetector`**

Create `tests/test_state.py`:

```python
"""Tests for bot.state — pixel-based game state detection."""
import pytest
from unittest.mock import MagicMock
from PIL import Image
import numpy as np

from bot.state import GameStateDetector, GameState
import config


def make_solid_image(color: tuple) -> Image.Image:
    """Create a 720x1280 solid color test image."""
    return Image.new("RGB", (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), color=color)


class TestGameStateEnum:
    """Test GameState enum values."""

    def test_has_expected_states(self):
        assert GameState.UNKNOWN is not None
        assert GameState.MENU is not None
        assert GameState.BATTLE is not None
        assert GameState.GAME_OVER is not None


class TestElixirCount:
    """Test elixir counting from pixel colors."""

    def test_returns_0_for_black_elixir_bar(self):
        # All-black image = no elixir pips filled
        img = make_solid_image((0, 0, 0))
        mock_capture = MagicMock()
        detector = GameStateDetector(mock_capture)
        count = detector.get_elixir_count(img)
        assert count == 0

    def test_returns_10_for_fully_purple_elixir_bar(self):
        # Create image with purple elixir bar region
        img = make_solid_image((0, 0, 0))
        pixels = np.array(img)
        # Fill elixir bar row with purple
        y = config.ELIXIR_BAR_Y
        pixels[y, config.ELIXIR_BAR_X_START:config.ELIXIR_BAR_X_END] = [200, 50, 200]
        img = Image.fromarray(pixels)

        mock_capture = MagicMock()
        detector = GameStateDetector(mock_capture)
        count = detector.get_elixir_count(img)
        assert count == 10

    def test_returns_int_between_0_and_10(self):
        img = make_solid_image((100, 100, 100))
        mock_capture = MagicMock()
        detector = GameStateDetector(mock_capture)
        count = detector.get_elixir_count(img)
        assert isinstance(count, int)
        assert 0 <= count <= 10


class TestDetectState:
    """Test overall game state detection."""

    def test_returns_game_state_enum(self):
        img = make_solid_image((100, 100, 100))
        mock_capture = MagicMock()
        mock_capture.capture.return_value = img
        detector = GameStateDetector(mock_capture)
        state = detector.detect(img)
        assert isinstance(state, GameState)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.state'`

**Step 3: Implement `bot/state.py`**

```python
"""Pixel-based game state detection for ClashBot.

Analyzes screenshot pixel colors to determine:
- Current screen (menu, battle, game over)
- Elixir count
- Basic battle state info

Phase 1: Simple pixel color checks. No ML.
Phase 2+: Will be augmented/replaced by YOLO detections.
"""
import logging
from enum import Enum

import numpy as np
from PIL import Image

import config

logger = logging.getLogger(__name__)


class GameState(Enum):
    """Possible game screen states."""
    UNKNOWN = "unknown"
    MENU = "menu"
    BATTLE = "battle"
    GAME_OVER = "game_over"


class GameStateDetector:
    """Detects game state from screenshots using pixel analysis."""

    def __init__(self, screen_capture):
        """
        Args:
            screen_capture: A ScreenCapture instance for taking screenshots.
        """
        self._screen = screen_capture

    def _pixel_in_range(self, pixel: tuple, color_min: tuple, color_max: tuple) -> bool:
        """Check if a pixel RGB value falls within a color range."""
        return all(lo <= val <= hi for val, lo, hi in zip(pixel, color_min, color_max))

    def get_elixir_count(self, image: Image.Image) -> int:
        """Count current elixir by checking pip colors on the elixir bar.

        Samples pixels along the elixir bar row. Each filled pip
        has a purple/pink color; unfilled pips are dark.

        Args:
            image: Screenshot as PIL Image (720x1280).

        Returns:
            Integer elixir count (0-10).
        """
        pixels = np.array(image)
        y = config.ELIXIR_BAR_Y
        x_start = config.ELIXIR_BAR_X_START
        x_end = config.ELIXIR_BAR_X_END

        # Sample one pixel per pip position
        pip_width = (x_end - x_start) / config.ELIXIR_PIP_COUNT
        filled = 0

        for i in range(config.ELIXIR_PIP_COUNT):
            x = int(x_start + pip_width * i + pip_width / 2)
            if y >= pixels.shape[0] or x >= pixels.shape[1]:
                continue
            pixel = tuple(pixels[y, x])
            if self._pixel_in_range(
                pixel,
                config.ELIXIR_FILLED_COLOR_MIN,
                config.ELIXIR_FILLED_COLOR_MAX,
            ):
                filled += 1

        logger.debug("Elixir count: %d", filled)
        return filled

    def detect(self, image: Image.Image) -> GameState:
        """Detect the current game state from a screenshot.

        Uses pixel color checks at known indicator positions to
        determine if we're in the menu, in battle, or at game over.

        Args:
            image: Screenshot as PIL Image (720x1280).

        Returns:
            GameState enum value.
        """
        pixels = np.array(image)

        # Check battle indicator position
        bx, by = config.BATTLE_INDICATOR_POS
        if by < pixels.shape[0] and bx < pixels.shape[1]:
            battle_pixel = tuple(pixels[by, bx])
            if self._pixel_in_range(
                battle_pixel,
                config.BATTLE_INDICATOR_COLOR_MIN,
                config.BATTLE_INDICATOR_COLOR_MAX,
            ):
                return GameState.BATTLE

        # TODO: Add more robust detection in Phase 2
        # For now, default to MENU if not clearly in battle
        return GameState.MENU

    def capture_and_detect(self) -> tuple[GameState, Image.Image]:
        """Capture a screenshot and detect the game state.

        Returns:
            Tuple of (GameState, PIL Image).
        """
        image = self._screen.capture()
        state = self.detect(image)
        return state, image
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_state.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add bot/state.py tests/test_state.py
git commit -m "feat: pixel-based game state detection (elixir, battle/menu)"
```

---

## Task 5: Strategy Module (Random)

**Files:**
- Create: `bot/strategy.py`
- Create: `tests/test_strategy.py`

**Depends on:** Task 4 (state.py — uses GameState), Task 1 (config.py)

**Step 1: Write failing tests for `RandomStrategy`**

Create `tests/test_strategy.py`:

```python
"""Tests for bot.strategy — decision engine (Phase 1: random)."""
import pytest
from unittest.mock import patch

from bot.strategy import RandomStrategy, Action
import config


class TestAction:
    """Test the Action data class."""

    def test_action_has_required_fields(self):
        action = Action(slot=0, x=180, y=530)
        assert action.slot == 0
        assert action.x == 180
        assert action.y == 530

    def test_no_action_returns_none(self):
        result = RandomStrategy().decide(elixir=0)
        assert result is None


class TestRandomStrategy:
    """Test random card placement strategy."""

    def test_returns_none_when_elixir_below_threshold(self):
        strategy = RandomStrategy()
        result = strategy.decide(elixir=3)
        assert result is None

    def test_returns_action_when_elixir_above_threshold(self):
        strategy = RandomStrategy()
        result = strategy.decide(elixir=config.ELIXIR_WAIT_THRESHOLD)
        assert result is not None
        assert isinstance(result, Action)

    def test_action_slot_is_valid(self):
        strategy = RandomStrategy()
        for _ in range(50):
            result = strategy.decide(elixir=10)
            assert 0 <= result.slot <= 3

    def test_action_position_is_within_arena(self):
        strategy = RandomStrategy()
        for _ in range(50):
            result = strategy.decide(elixir=10)
            assert config.ARENA_LEFT_X <= result.x <= config.ARENA_RIGHT_X
            assert config.ARENA_BRIDGE_Y <= result.y <= config.ARENA_BOTTOM_Y
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_strategy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.strategy'`

**Step 3: Implement `bot/strategy.py`**

```python
"""Decision engine for ClashBot.

Phase 1: Random card placement.
- Waits until elixir >= threshold
- Picks a random card slot (0-3)
- Picks a random arena position (biased toward bridges)

Phase 3+: Will be replaced by heuristic/ML-based strategy.
"""
import logging
import random
from dataclasses import dataclass

import config

logger = logging.getLogger(__name__)


@dataclass
class Action:
    """A card play action."""
    slot: int  # Card slot 0-3
    x: int     # Arena X coordinate
    y: int     # Arena Y coordinate


class RandomStrategy:
    """Phase 1 strategy: play random cards at random positions."""

    def decide(self, elixir: int) -> Action | None:
        """Decide what action to take based on current elixir.

        Args:
            elixir: Current elixir count (0-10).

        Returns:
            An Action to play, or None if we should wait.
        """
        if elixir < config.ELIXIR_WAIT_THRESHOLD:
            return None

        slot = random.randint(0, 3)

        # Bias placement toward the two bridge positions
        # 60% chance bridge, 40% random arena position
        if random.random() < 0.6:
            x, y = random.choice([config.LEFT_BRIDGE, config.RIGHT_BRIDGE])
        else:
            x = random.randint(config.ARENA_LEFT_X, config.ARENA_RIGHT_X)
            y = random.randint(config.ARENA_BRIDGE_Y, config.ARENA_BOTTOM_Y)

        action = Action(slot=slot, x=x, y=y)
        logger.info("Decision: play slot %d at (%d, %d) [elixir=%d]", slot, x, y, elixir)
        return action
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_strategy.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add bot/strategy.py tests/test_strategy.py
git commit -m "feat: random card strategy (Phase 1 decision engine)"
```

---

## Task 6: Main Game Loop + Integration

**Files:**
- Create: `main.py`
- Create: `tests/test_pipeline.py`

**Depends on:** ALL previous tasks (2, 3, 4, 5)

**Step 1: Write integration test**

Create `tests/test_pipeline.py`:

```python
"""Integration test — verify the full pipeline connects."""
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from bot.screen import ScreenCapture
from bot.actions import ActionExecutor
from bot.state import GameStateDetector, GameState
from bot.strategy import RandomStrategy, Action


class TestPipelineIntegration:
    """Test that all modules connect correctly."""

    def test_full_pipeline_capture_to_action(self):
        """Verify: capture → detect state → strategy → action."""
        # Mock screen capture
        test_img = Image.new("RGB", (720, 1280), color=(0, 0, 0))
        mock_screen = MagicMock(spec=ScreenCapture)
        mock_screen.capture.return_value = test_img

        # State detection
        detector = GameStateDetector(mock_screen)
        state = detector.detect(test_img)
        assert isinstance(state, GameState)

        # Strategy
        strategy = RandomStrategy()
        action = strategy.decide(elixir=10)
        assert isinstance(action, Action)

        # Action execution (mocked)
        mock_executor = MagicMock(spec=ActionExecutor)
        mock_executor.play_card(action.slot, action.x, action.y)
        mock_executor.play_card.assert_called_once_with(action.slot, action.x, action.y)

    def test_strategy_returns_none_on_low_elixir(self):
        """Verify bot waits when elixir is low."""
        strategy = RandomStrategy()
        assert strategy.decide(elixir=3) is None
```

**Step 2: Run integration test**

Run: `pytest tests/test_pipeline.py -v`
Expected: All tests PASS

**Step 3: Implement `main.py`**

```python
"""ClashBot — Main entry point.

Runs the game loop:
1. Capture screenshot
2. Detect game state
3. If in battle: decide and play a card
4. If in menu: click the Battle button
5. If game over: wait and dismiss
"""
import logging
import sys
import time

import config
from bot.screen import ScreenCapture
from bot.actions import ActionExecutor
from bot.state import GameStateDetector, GameState
from bot.strategy import RandomStrategy

# --- Logging Setup ---
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE),
    ],
)
logger = logging.getLogger("clashbot")


def main():
    logger.info("ClashBot starting...")

    # Initialize components
    screen = ScreenCapture()
    executor = ActionExecutor()
    detector = GameStateDetector(screen)
    strategy = RandomStrategy()

    if not screen.is_connected():
        logger.error("Cannot connect to emulator. Is LDPlayer running with ADB enabled?")
        sys.exit(1)

    logger.info("Connected to emulator. Starting game loop.")

    try:
        game_loop(screen, executor, detector, strategy)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C).")


def game_loop(screen, executor, detector, strategy):
    """Main game loop — runs until interrupted."""
    while True:
        state, image = detector.capture_and_detect()
        logger.info("State: %s", state.value)

        if state == GameState.BATTLE:
            elixir = detector.get_elixir_count(image)
            action = strategy.decide(elixir)
            if action:
                executor.play_card(action.slot, action.x, action.y)
            else:
                logger.debug("Waiting for elixir... (%d/%d)", elixir, config.ELIXIR_WAIT_THRESHOLD)

        elif state == GameState.MENU:
            logger.info("In menu — clicking Battle button.")
            executor.tap(*config.BATTLE_BUTTON)

        elif state == GameState.GAME_OVER:
            logger.info("Game over — waiting and dismissing.")
            time.sleep(config.POST_GAME_WAIT)
            executor.tap(*config.OK_BUTTON)

        else:
            logger.debug("Unknown state — waiting.")

        time.sleep(config.CAPTURE_INTERVAL)


if __name__ == "__main__":
    main()
```

**Step 4: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests across all modules PASS

**Step 5: Manual smoke test (requires emulator running)**

```bash
python main.py
```

Watch: Bot should connect, detect the menu, click Battle, enter a game, and start (badly) playing cards. It will lose. That's success.

**Step 6: Commit**

```bash
git add main.py tests/test_pipeline.py
git commit -m "feat: main game loop — complete Phase 1 pipeline"
```

---

## Phase 1 Completion Criteria

- [ ] `pytest tests/ -v` — all tests pass
- [ ] `python main.py` — bot connects, enters battle, plays random cards
- [ ] Bot survives a full game cycle: menu → battle → game over → menu (repeat)
- [ ] Logs written to `clashbot.log` with state transitions visible
- [ ] All coordinates work correctly at 720x1280 in LDPlayer 9

## Notes for Agents

- **Do NOT change config.py coordinates without testing on the actual emulator.** The values in this plan are educated guesses based on 720x1280 layout. They WILL need calibration during the manual smoke test.
- **The `pure-python-adb` package imports as `ppadb`**, not `pure_python_adb`. This is a common gotcha.
- **`device.screencap()` returns raw bytes** — the `shell()` method is different. Use `screencap()` for screenshots.
- If ADB connection fails, the user needs to: (1) make sure LDPlayer is running, (2) check ADB is enabled in settings, (3) possibly run `adb connect 127.0.0.1:<port>` manually first.
