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
