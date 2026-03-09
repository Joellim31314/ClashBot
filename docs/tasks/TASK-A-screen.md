# Task A: Screen Capture Module

> **Context:** Read `CLAUDE.md` and `config.py` first. Do NOT modify `config.py`.

## Your Job
Create `bot/screen.py` and `tests/test_screen.py`. Nothing else.

## Files You Own
- **Create:** `bot/screen.py`
- **Create:** `tests/test_screen.py`
- **Read only:** `config.py` (import from it, never edit)

## DO NOT TOUCH
- `bot/actions.py`, `bot/state.py`, `bot/strategy.py`, `main.py` — other agents handle these

## What To Build

`ScreenCapture` class that:
1. Connects to ADB using `ppadb.client.Client` (note: `pure-python-adb` imports as `ppadb`)
2. Uses `config.ADB_HOST` and `config.ADB_PORT` for connection
3. `is_connected()` → returns `bool`
4. `capture()` → returns `PIL.Image.Image` (720x1280 RGB). Raises `ConnectionError` if no device.
5. `reconnect()` → re-attempts ADB connection

### Implementation

```python
"""ADB screen capture module for ClashBot."""
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
        devices = self._client.devices()
        if devices:
            self._device = devices[0]
            logger.info("Connected to device: %s", self._device.serial)
        else:
            logger.warning("No ADB devices found. Is the emulator running?")

    def is_connected(self) -> bool:
        return self._device is not None

    def capture(self) -> Image.Image:
        if not self.is_connected():
            raise ConnectionError("No ADB device connected. Start the emulator first.")
        png_bytes = self._device.screencap()
        image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        logger.debug("Captured frame: %s", image.size)
        return image

    def reconnect(self):
        logger.info("Attempting ADB reconnection...")
        self._device = None
        self._connect()
```

### Tests

```python
"""Tests for bot.screen — ADB screen capture module."""
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from bot.screen import ScreenCapture
import config


class TestScreenCaptureInit:
    @patch("bot.screen.AdbClient")
    def test_creates_adb_client_with_config(self, mock_adb_cls):
        mock_client = MagicMock()
        mock_client.devices.return_value = [MagicMock()]
        mock_adb_cls.return_value = mock_client
        sc = ScreenCapture()
        mock_adb_cls.assert_called_once_with(host=config.ADB_HOST, port=config.ADB_PORT)

    @patch("bot.screen.AdbClient")
    def test_is_connected_true_when_device_found(self, mock_adb_cls):
        mock_client = MagicMock()
        mock_client.devices.return_value = [MagicMock()]
        mock_adb_cls.return_value = mock_client
        assert ScreenCapture().is_connected() is True

    @patch("bot.screen.AdbClient")
    def test_is_connected_false_when_no_devices(self, mock_adb_cls):
        mock_client = MagicMock()
        mock_client.devices.return_value = []
        mock_adb_cls.return_value = mock_client
        assert ScreenCapture().is_connected() is False


class TestScreenCapture:
    @patch("bot.screen.AdbClient")
    def test_capture_returns_pil_image(self, mock_adb_cls):
        import io as _io
        test_img = Image.new("RGB", (720, 1280), color=(100, 100, 100))
        buf = _io.BytesIO()
        test_img.save(buf, format="PNG")

        mock_device = MagicMock()
        mock_device.screencap.return_value = buf.getvalue()
        mock_client = MagicMock()
        mock_client.devices.return_value = [mock_device]
        mock_adb_cls.return_value = mock_client

        result = ScreenCapture().capture()
        assert isinstance(result, Image.Image)
        assert result.size == (720, 1280)

    @patch("bot.screen.AdbClient")
    def test_capture_raises_when_not_connected(self, mock_adb_cls):
        mock_client = MagicMock()
        mock_client.devices.return_value = []
        mock_adb_cls.return_value = mock_client
        with pytest.raises(ConnectionError):
            ScreenCapture().capture()
```

## Verify

```bash
pytest tests/test_screen.py -v
```

All 5 tests should PASS.

## Commit

```bash
git add bot/screen.py tests/test_screen.py
git commit -m "feat: ADB screen capture module with tests"
```
