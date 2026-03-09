# Task B: Action Executor Module

> **Context:** Read `CLAUDE.md` and `config.py` first. Do NOT modify `config.py`.

## Your Job
Create `bot/actions.py` and `tests/test_actions.py`. Nothing else.

## Files You Own
- **Create:** `bot/actions.py`
- **Create:** `tests/test_actions.py`
- **Read only:** `config.py` (import from it, never edit)

## DO NOT TOUCH
- `bot/screen.py`, `bot/state.py`, `bot/strategy.py`, `main.py` — other agents handle these

## What To Build

`ActionExecutor` class that:
1. Connects to ADB using `ppadb.client.Client` (note: `pure-python-adb` imports as `ppadb`)
2. `tap(x, y)` → sends `input tap X Y` shell command. Raises `ConnectionError` if no device.
3. `swipe(x1, y1, x2, y2, duration_ms)` → sends `input swipe` command.
4. `play_card(slot, x, y)` → taps card slot position from `config.CARD_SLOT_X[slot]`/`config.CARD_SLOT_Y`, then taps arena position. Raises `ValueError` if slot not 0-3.
5. Adds random human-like delay between the two taps in `play_card` using `config.ACTION_DELAY_MIN`/`MAX`.

### Implementation

```python
"""ADB action execution module for ClashBot."""
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
        devices = self._client.devices()
        if devices:
            self._device = devices[0]
            logger.info("ActionExecutor connected to: %s", self._device.serial)
        else:
            logger.warning("No ADB devices found.")

    def is_connected(self) -> bool:
        return self._device is not None

    def _ensure_connected(self):
        if not self.is_connected():
            raise ConnectionError("No ADB device connected.")

    def _random_delay(self):
        delay = random.uniform(config.ACTION_DELAY_MIN, config.ACTION_DELAY_MAX)
        time.sleep(delay)

    def tap(self, x: int, y: int):
        self._ensure_connected()
        self._device.shell(f"input tap {x} {y}")
        logger.debug("Tapped (%d, %d)", x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        self._ensure_connected()
        self._device.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")
        logger.debug("Swiped (%d,%d) -> (%d,%d)", x1, y1, x2, y2)

    def play_card(self, slot: int, x: int, y: int):
        if slot < 0 or slot > 3:
            raise ValueError(f"Invalid slot {slot}: must be 0-3")
        self._ensure_connected()

        card_x = config.CARD_SLOT_X[slot]
        card_y = config.CARD_SLOT_Y
        self._device.shell(f"input tap {card_x} {card_y}")
        self._random_delay()
        self._device.shell(f"input tap {x} {y}")
        logger.info("Played card slot %d -> (%d, %d)", slot, x, y)
```

### Tests

```python
"""Tests for bot.actions — ADB action execution module."""
import pytest
from unittest.mock import MagicMock, patch, call

from bot.actions import ActionExecutor
import config


class TestActionExecutorTap:
    @patch("bot.actions.AdbClient")
    def test_tap_sends_correct_adb_command(self, mock_adb_cls):
        mock_device = MagicMock()
        mock_client = MagicMock()
        mock_client.devices.return_value = [mock_device]
        mock_adb_cls.return_value = mock_client

        ActionExecutor().tap(360, 640)
        mock_device.shell.assert_called_once_with("input tap 360 640")

    @patch("bot.actions.AdbClient")
    def test_tap_raises_when_not_connected(self, mock_adb_cls):
        mock_client = MagicMock()
        mock_client.devices.return_value = []
        mock_adb_cls.return_value = mock_client

        with pytest.raises(ConnectionError):
            ActionExecutor().tap(360, 640)


class TestActionExecutorPlayCard:
    @patch("bot.actions.time")
    @patch("bot.actions.AdbClient")
    def test_play_card_taps_slot_then_arena(self, mock_adb_cls, mock_time):
        mock_device = MagicMock()
        mock_client = MagicMock()
        mock_client.devices.return_value = [mock_device]
        mock_adb_cls.return_value = mock_client

        ActionExecutor().play_card(slot=0, x=180, y=530)

        calls = mock_device.shell.call_args_list
        assert calls[0] == call(f"input tap {config.CARD_SLOT_X[0]} {config.CARD_SLOT_Y}")
        assert calls[1] == call("input tap 180 530")

    @patch("bot.actions.AdbClient")
    def test_play_card_validates_slot_range(self, mock_adb_cls):
        mock_device = MagicMock()
        mock_client = MagicMock()
        mock_client.devices.return_value = [mock_device]
        mock_adb_cls.return_value = mock_client

        with pytest.raises(ValueError, match="slot"):
            ActionExecutor().play_card(slot=5, x=180, y=530)


class TestActionExecutorSwipe:
    @patch("bot.actions.AdbClient")
    def test_swipe_sends_correct_adb_command(self, mock_adb_cls):
        mock_device = MagicMock()
        mock_client = MagicMock()
        mock_client.devices.return_value = [mock_device]
        mock_adb_cls.return_value = mock_client

        ActionExecutor().swipe(100, 200, 300, 400, duration_ms=300)
        mock_device.shell.assert_called_once_with("input swipe 100 200 300 400 300")
```

## Verify

```bash
pytest tests/test_actions.py -v
```

All 5 tests should PASS.

## Commit

```bash
git add bot/actions.py tests/test_actions.py
git commit -m "feat: ADB action executor with tap, swipe, and play_card"
```
