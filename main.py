"""ClashBot — Main entry point."""
import logging
import sys
import time

import config
from bot.screen import ScreenCapture
from bot.actions import ActionExecutor
from bot.state import GameStateDetector, GameState
from bot.strategy import RandomStrategy

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
    while True:
        state, image = detector.capture_and_detect()
        logger.info("State: %s", state.value)

        if state == GameState.BATTLE:
            elixir = detector.get_elixir_count(image)
            logger.info("Elixir: %d", elixir)
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

        elif state == GameState.CHEST:
            logger.info("Chest popup — tapping to dismiss.")
            for _ in range(config.CHEST_TAP_COUNT):
                executor.tap(*config.CHEST_TAP_POS)
                time.sleep(0.4)

        elif state == GameState.TROPHY_ROAD:
            logger.info("Trophy road — pressing OK.")
            executor.tap(*config.TROPHY_ROAD_OK_BUTTON)

        elif state == GameState.UNKNOWN:
            logger.debug("Unknown state — no indicator matched. Waiting...")

        time.sleep(config.CAPTURE_INTERVAL)


if __name__ == "__main__":
    main()
