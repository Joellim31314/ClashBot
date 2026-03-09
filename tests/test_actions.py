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
