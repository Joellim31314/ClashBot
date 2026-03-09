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
