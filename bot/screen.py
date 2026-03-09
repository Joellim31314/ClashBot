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
