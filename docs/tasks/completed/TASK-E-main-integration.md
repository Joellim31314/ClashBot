# Task E: Main Game Loop + Integration Tests

> **Context:** Read `CLAUDE.md` and `config.py` first. Do NOT modify `config.py`.

## IMPORTANT: Run this AFTER Tasks A-D are all complete
This task imports from ALL four bot modules. Do not start until `bot/screen.py`, `bot/actions.py`, `bot/state.py`, and `bot/strategy.py` all exist and their tests pass.

## Your Job
Create `main.py` and `tests/test_pipeline.py`. Nothing else.

## Files You Own
- **Create:** `main.py`
- **Create:** `tests/test_pipeline.py`
- **Read only:** Everything else

## What To Build

### main.py — Entry Point

Game loop that:
1. Initializes `ScreenCapture`, `ActionExecutor`, `GameStateDetector`, `RandomStrategy`
2. Exits with error if emulator not connected
3. Loops forever (until Ctrl+C):
   - `BATTLE` state → read elixir, call `strategy.decide()`, if action → `executor.play_card()`
   - `MENU` state → tap `config.BATTLE_BUTTON`
   - `GAME_OVER` state → wait `config.POST_GAME_WAIT`, tap `config.OK_BUTTON`
   - Sleep `config.CAPTURE_INTERVAL` between iterations
4. Uses `logging` module (not print), writes to stdout + `config.LOG_FILE`

### Implementation

```python
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

        time.sleep(config.CAPTURE_INTERVAL)


if __name__ == "__main__":
    main()
```

### Integration Tests

```python
"""Integration test — verify the full pipeline connects."""
import pytest
from unittest.mock import MagicMock
from PIL import Image

from bot.screen import ScreenCapture
from bot.actions import ActionExecutor
from bot.state import GameStateDetector, GameState
from bot.strategy import RandomStrategy, Action


class TestPipelineIntegration:
    def test_full_pipeline_capture_to_action(self):
        test_img = Image.new("RGB", (720, 1280), color=(0, 0, 0))
        mock_screen = MagicMock(spec=ScreenCapture)
        mock_screen.capture.return_value = test_img

        detector = GameStateDetector(mock_screen)
        state = detector.detect(test_img)
        assert isinstance(state, GameState)

        strategy = RandomStrategy()
        action = strategy.decide(elixir=10)
        assert isinstance(action, Action)

        mock_executor = MagicMock(spec=ActionExecutor)
        mock_executor.play_card(action.slot, action.x, action.y)
        mock_executor.play_card.assert_called_once_with(action.slot, action.x, action.y)

    def test_strategy_returns_none_on_low_elixir(self):
        assert RandomStrategy().decide(elixir=3) is None

    def test_capture_and_detect_wires_correctly(self):
        test_img = Image.new("RGB", (720, 1280), color=(0, 0, 0))
        mock_screen = MagicMock()
        mock_screen.capture.return_value = test_img

        detector = GameStateDetector(mock_screen)
        state, image = detector.capture_and_detect()

        assert isinstance(state, GameState)
        assert image is test_img
        mock_screen.capture.assert_called_once()
```

## Verify

```bash
# Run integration tests
pytest tests/test_pipeline.py -v

# Run ALL tests to make sure nothing broke
pytest tests/ -v
```

All tests should PASS.

## Commit

```bash
git add main.py tests/test_pipeline.py
git commit -m "feat: main game loop — complete Phase 1 pipeline"
```
