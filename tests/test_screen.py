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
