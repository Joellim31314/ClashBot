"""Screen capture module for ClashBot.

Uses DXCam on Windows for low-latency capture when available, and keeps ADB
as a fallback for compatibility.
"""
import io
import logging
import platform
import time
from typing import Optional

from PIL import Image
from ppadb.client import Client as AdbClient

import config

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Captures screenshots from the emulator.

    Priority:
    1) DXCam + LDPlayer window capture (fast)
    2) ADB screencap fallback (reliable when window capture is unavailable)
    """

    WINDOW_KEYWORDS = ("ldplayer", "ldmultiplayer", "dnplayer", "clash royale")

    def __init__(self, use_dxcam: bool = True):
        self._use_dxcam = use_dxcam
        self._client = None
        self._device = None
        self._dxcam = None
        self._region: Optional[tuple[int, int, int, int]] = None

        if self._use_dxcam and platform.system() == "Windows":
            self._init_dxcam()

        if self._dxcam is None:
            self._init_adb()

    def _init_dxcam(self):
        """Initialize DXCam and resolve the emulator window region."""
        try:
            import dxcam
        except ImportError:
            logger.info("DXCam not installed; using ADB fallback")
            return

        try:
            self._dxcam = dxcam.create(output_color="RGB")
            self._region = self._find_emulator_window()
            if self._region is None:
                logger.warning("DXCam initialized but no LDPlayer window found; using ADB fallback")
                self._dxcam = None
            else:
                logger.info("DXCam capture initialized for region %s", self._region)
        except Exception as exc:
            logger.warning("DXCam init failed: %s", exc)
            self._dxcam = None
            self._region = None

    def _find_emulator_window(self) -> Optional[tuple[int, int, int, int]]:
        """Find a visible LDPlayer window and return its client rect on screen."""
        try:
            import win32gui
        except ImportError:
            logger.info("pywin32 not installed; cannot discover LDPlayer window for DXCam")
            return None

        matches: list[tuple[int, tuple[int, int, int, int], str]] = []

        def _enum_cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return True
            if not any(k in title.lower() for k in self.WINDOW_KEYWORDS):
                return True

            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            if right <= left or bottom <= top:
                return True
            screen_left, screen_top = win32gui.ClientToScreen(hwnd, (left, top))
            screen_right, screen_bottom = win32gui.ClientToScreen(hwnd, (right, bottom))
            width = screen_right - screen_left
            height = screen_bottom - screen_top
            if width <= 0 or height <= 0:
                return True

            region = (screen_left, screen_top, screen_right, screen_bottom)
            matches.append((width * height, region, title))
            return True

        win32gui.EnumWindows(_enum_cb, None)
        if not matches:
            return None

        _, region, title = max(matches, key=lambda x: x[0])
        logger.info("DXCam selected window '%s' with region %s", title, region)
        return region

    def _init_adb(self):
        """Initialize ADB fallback capture."""
        try:
            self._client = AdbClient(host=config.ADB_HOST, port=config.ADB_PORT)
            devices = self._client.devices()
            if devices:
                self._device = devices[0]
                logger.info("ADB connected to device: %s", self._device.serial)
            else:
                logger.warning("No ADB devices found. Is the emulator running?")
        except Exception as exc:
            logger.warning("ADB init failed: %s", exc)
            self._client = None
            self._device = None

    def is_connected(self) -> bool:
        return self._dxcam is not None or self._device is not None

    def _normalize_image(self, image: Image.Image) -> Image.Image:
        """Guarantee RGB mode and project resolution for downstream consumers."""
        if image.mode != "RGB":
            image = image.convert("RGB")
        target_size = (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        if image.size != target_size:
            image = image.resize(target_size, Image.BILINEAR)
        return image

    def _capture_dxcam(self) -> Image.Image:
        frame = self._dxcam.grab(region=self._region)
        if frame is None:
            time.sleep(0.01)
            frame = self._dxcam.grab(region=self._region)
        if frame is None:
            raise RuntimeError("DXCam returned no frame; ensure emulator window is visible")

        if frame.ndim == 3 and frame.shape[2] >= 3:
            image = Image.fromarray(frame[:, :, :3], mode="RGB")
        else:
            image = Image.fromarray(frame).convert("RGB")
        image = self._normalize_image(image)
        logger.debug("DXCam frame: %s", image.size)
        return image

    def _capture_adb(self) -> Image.Image:
        png_bytes = self._device.screencap()
        image = Image.open(io.BytesIO(png_bytes))
        image = self._normalize_image(image)
        logger.debug("ADB frame: %s", image.size)
        return image

    def capture(self) -> Image.Image:
        if self._dxcam is not None and self._region is not None:
            try:
                return self._capture_dxcam()
            except Exception as exc:
                logger.warning("DXCam capture failed: %s", exc)
                if self._device is None:
                    self._init_adb()
                if self._device is not None:
                    logger.info("Falling back to ADB capture")
                    return self._capture_adb()
                raise

        if self._device is not None:
            return self._capture_adb()

        raise ConnectionError("No capture method available. Start emulator and reconnect.")

    def reconnect(self):
        logger.info("Attempting capture reconnection...")
        self._client = None
        self._device = None
        self._dxcam = None
        self._region = None
        if self._use_dxcam and platform.system() == "Windows":
            self._init_dxcam()
        if self._dxcam is None:
            self._init_adb()
