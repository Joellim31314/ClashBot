# Task D: Strategy Module (Random)

> **Context:** Read `CLAUDE.md` and `config.py` first. Do NOT modify `config.py`.

## Your Job
Create `bot/strategy.py` and `tests/test_strategy.py`. Nothing else.

## Files You Own
- **Create:** `bot/strategy.py`
- **Create:** `tests/test_strategy.py`
- **Read only:** `config.py` (import from it, never edit)

## DO NOT TOUCH
- `bot/screen.py`, `bot/actions.py`, `bot/state.py`, `main.py` — other agents handle these

## What To Build

`Action` dataclass and `RandomStrategy` class:

1. `Action(slot: int, x: int, y: int)` — a dataclass representing a card play
2. `RandomStrategy.decide(elixir: int) -> Action | None`
   - Returns `None` if `elixir < config.ELIXIR_WAIT_THRESHOLD`
   - Picks random slot 0-3
   - 60% chance: places at one of the two bridge positions (`config.LEFT_BRIDGE` or `config.RIGHT_BRIDGE`)
   - 40% chance: random position within arena bounds
   - Returns an `Action`

### Implementation

```python
"""Decision engine for ClashBot. Phase 1: Random card placement."""
import logging
import random
from dataclasses import dataclass

import config

logger = logging.getLogger(__name__)


@dataclass
class Action:
    slot: int  # Card slot 0-3
    x: int     # Arena X coordinate
    y: int     # Arena Y coordinate


class RandomStrategy:
    def decide(self, elixir: int) -> Action | None:
        if elixir < config.ELIXIR_WAIT_THRESHOLD:
            return None

        slot = random.randint(0, 3)

        if random.random() < 0.6:
            x, y = random.choice([config.LEFT_BRIDGE, config.RIGHT_BRIDGE])
        else:
            x = random.randint(config.ARENA_LEFT_X, config.ARENA_RIGHT_X)
            y = random.randint(config.ARENA_BRIDGE_Y, config.ARENA_BOTTOM_Y)

        action = Action(slot=slot, x=x, y=y)
        logger.info("Decision: play slot %d at (%d, %d) [elixir=%d]", slot, x, y, elixir)
        return action
```

### Tests

```python
"""Tests for bot.strategy — decision engine (Phase 1: random)."""
import pytest

from bot.strategy import RandomStrategy, Action
import config


class TestAction:
    def test_action_has_required_fields(self):
        action = Action(slot=0, x=180, y=530)
        assert action.slot == 0
        assert action.x == 180
        assert action.y == 530


class TestRandomStrategy:
    def test_returns_none_when_elixir_below_threshold(self):
        assert RandomStrategy().decide(elixir=3) is None

    def test_returns_none_at_zero_elixir(self):
        assert RandomStrategy().decide(elixir=0) is None

    def test_returns_action_when_elixir_at_threshold(self):
        result = RandomStrategy().decide(elixir=config.ELIXIR_WAIT_THRESHOLD)
        assert result is not None
        assert isinstance(result, Action)

    def test_returns_action_when_elixir_above_threshold(self):
        result = RandomStrategy().decide(elixir=10)
        assert isinstance(result, Action)

    def test_action_slot_is_valid(self):
        strategy = RandomStrategy()
        for _ in range(50):
            result = strategy.decide(elixir=10)
            assert 0 <= result.slot <= 3

    def test_action_position_is_within_arena(self):
        strategy = RandomStrategy()
        for _ in range(50):
            result = strategy.decide(elixir=10)
            assert config.ARENA_LEFT_X <= result.x <= config.ARENA_RIGHT_X
            assert config.ARENA_BRIDGE_Y <= result.y <= config.ARENA_BOTTOM_Y
```

## Verify

```bash
pytest tests/test_strategy.py -v
```

All 6 tests should PASS.

## Commit

```bash
git add bot/strategy.py tests/test_strategy.py
git commit -m "feat: random card strategy (Phase 1 decision engine)"
```
