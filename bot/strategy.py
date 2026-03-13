"""Decision engine for ClashBot. Phase 1: Random card placement."""
import logging
import random

import config
from bot.models import Action, BattleScene

logger = logging.getLogger(__name__)


class RandomStrategy:
    def decide(self, scene: BattleScene) -> Action | None:
        if scene.elixir < config.ELIXIR_WAIT_THRESHOLD:
            return None

        slot = random.randint(0, 3)

        if random.random() < 0.6:
            x, y = random.choice([config.LEFT_BRIDGE, config.RIGHT_BRIDGE])
        else:
            x = random.randint(config.ARENA_LEFT_X, config.ARENA_RIGHT_X)
            y = random.randint(config.ARENA_BRIDGE_Y, config.ARENA_BOTTOM_Y)

        action = Action(slot=slot, x=x, y=y)
        logger.info("Decision: play slot %d at (%d, %d) [elixir=%d]", slot, x, y, scene.elixir)
        return action
