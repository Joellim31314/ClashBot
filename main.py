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


def _init_vision():
    """Try to initialize YOLO detector and card matcher. Returns (detector, matcher) or (None, None)."""
    yolo_detector = None
    card_matcher = None

    try:
        from bot.vision import YOLODetector, CardMatcher
        yolo_detector = YOLODetector()
        if yolo_detector.is_loaded:
            logger.info("YOLO detector enabled.")
        else:
            logger.info("YOLO detector disabled (model not found). Running in Phase 1 mode.")
            yolo_detector = None

        card_matcher = CardMatcher()
        if card_matcher.is_loaded:
            logger.info("Card matcher enabled (%d templates).", len(card_matcher._templates))
        else:
            logger.info("Card matcher disabled (no templates). Cards will be 'unknown'.")
            card_matcher = None
    except Exception:
        logger.warning("Vision modules unavailable. Running in Phase 1 mode.", exc_info=True)

    return yolo_detector, card_matcher


def main():
    logger.info("ClashBot starting...")

    screen = ScreenCapture()
    executor = ActionExecutor()

    yolo_detector, card_matcher = _init_vision()
    detector = GameStateDetector(screen, yolo_detector=yolo_detector, card_matcher=card_matcher)
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
            scene = detector.get_battle_scene(image)
            action = strategy.decide(scene)
            if action:
                executor.play_card(action.slot, action.x, action.y)
            else:
                logger.debug("Waiting for elixir... (%d/%d)", scene.elixir, config.ELIXIR_WAIT_THRESHOLD)

        elif state == GameState.MENU:
            logger.info("In menu — clicking Battle button.")
            executor.tap(*config.BATTLE_BUTTON)

        elif state == GameState.GAME_OVER:
            logger.info("Game over — waiting and dismissing.")
            time.sleep(config.POST_GAME_WAIT)
            executor.tap(*config.OK_BUTTON)

        elif state == GameState.TROPHY_ROAD:
            logger.info("Trophy road — pressing OK.")
            executor.tap(*config.TROPHY_ROAD_OK_BUTTON)
            time.sleep(2.0)  # Wait for transition back to menu

        elif state == GameState.UNKNOWN:
            logger.info("Unknown state — assuming Chest or overlay. Tapping to dismiss.")
            for _ in range(config.CHEST_TAP_COUNT):
                executor.tap(*config.CHEST_TAP_POS)
                time.sleep(0.2)

        time.sleep(config.CAPTURE_INTERVAL)


if __name__ == "__main__":
    main()
