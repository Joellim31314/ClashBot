"""Decision engine for ClashBot.

Phase 1: RandomStrategy — random card placement.
Phase 3: HogStrategy — Hog 2.6 heuristic rules (defend → attack → cycle).
"""
import logging
import random

import config
from bot.models import Action, BattleScene, Detection

logger = logging.getLogger(__name__)


class RandomStrategy:
    """Phase 1: Play random cards when elixir is high."""

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


class HogStrategy:
    """Phase 3: Hog 2.6 heuristic strategy.

    Decision priority: DEFEND → ATTACK → CYCLE → WAIT.
    Uses cards in hand, elixir count, and YOLO detections.
    """

    def decide(self, scene: BattleScene) -> Action | None:
        hand = self._get_playable_cards(scene)
        if not hand:
            logger.debug("No playable cards (elixir=%d)", scene.elixir)
            return None

        # Separate detections by arena side (friendly side = potential threat)
        threats = [d for d in scene.detections if d.side == "friendly"]
        has_air = any(d.class_name in config.AIR_TROOPS for d in threats)

        # --- DEFEND ---
        if threats:
            action = self._defend(scene, hand, threats, has_air)
            if action:
                return action

        # --- ATTACK ---
        action = self._attack(scene, hand)
        if action:
            return action

        # --- CYCLE ---
        action = self._cycle(scene, hand)
        if action:
            return action

        return None

    def _get_playable_cards(self, scene: BattleScene) -> dict[str, int]:
        """Return {card_name: slot} for cards in hand we can afford."""
        playable = {}
        for card in scene.cards_in_hand:
            if card.card_name == "unknown":
                continue
            cost = config.HOG_DECK.get(card.card_name, {}).get("cost")
            if cost is not None and scene.elixir >= cost:
                playable[card.card_name] = card.slot
        return playable

    def _defend(self, scene: BattleScene, hand: dict[str, int],
                threats: list[Detection], has_air: bool) -> Action | None:
        """React to enemy troops on our side of the arena."""
        # Air threat → Musketeer
        if has_air and "musketeer" in hand:
            x, y = config.MUSKETEER_BEHIND_KING
            logger.info("DEFEND: Musketeer vs air threat [elixir=%d]", scene.elixir)
            return Action(slot=hand["musketeer"], x=x, y=y)

        # Ground threat → Cannon (center pull)
        if "cannon" in hand:
            x, y = config.CANNON_PULL_CENTER
            logger.info("DEFEND: Cannon center pull [elixir=%d]", scene.elixir)
            return Action(slot=hand["cannon"], x=x, y=y)

        # No cannon → Musketeer for ground too
        if "musketeer" in hand:
            x, y = config.MUSKETEER_BEHIND_KING
            logger.info("DEFEND: Musketeer vs ground [elixir=%d]", scene.elixir)
            return Action(slot=hand["musketeer"], x=x, y=y)

        # Cheap defense → Skeletons or Ice Spirit on the threat
        threat_pos = (threats[0].center[0], threats[0].center[1])
        for card_name in ("skeletons", "ice-spirit", "ice-golem"):
            if card_name in hand:
                logger.info("DEFEND: %s on threat at (%d,%d) [elixir=%d]",
                            card_name, *threat_pos, scene.elixir)
                return Action(slot=hand[card_name], x=threat_pos[0], y=threat_pos[1])

        return None

    def _attack(self, scene: BattleScene, hand: dict[str, int]) -> Action | None:
        """Play Hog Rider at bridge when safe and elixir is comfortable."""
        if "hog-rider" in hand and scene.elixir >= 7:
            x, y = random.choice([config.LEFT_BRIDGE, config.RIGHT_BRIDGE])
            logger.info("ATTACK: Hog Rider at bridge (%d,%d) [elixir=%d]", x, y, scene.elixir)
            return Action(slot=hand["hog-rider"], x=x, y=y)

        # Leaking elixir → play something
        if scene.elixir >= 10:
            if "hog-rider" in hand:
                x, y = random.choice([config.LEFT_BRIDGE, config.RIGHT_BRIDGE])
                logger.info("ATTACK: Hog Rider (leaking elixir) [elixir=%d]", scene.elixir)
                return Action(slot=hand["hog-rider"], x=x, y=y)
            if "musketeer" in hand:
                x, y = config.MUSKETEER_BEHIND_KING
                logger.info("ATTACK: Musketeer behind king (leaking) [elixir=%d]", scene.elixir)
                return Action(slot=hand["musketeer"], x=x, y=y)

        return None

    def _cycle(self, scene: BattleScene, hand: dict[str, int]) -> Action | None:
        """Cycle cheap cards at the back when there's nothing else to do."""
        if scene.elixir < 5:
            return None

        for card_name in ("skeletons", "ice-spirit"):
            if card_name in hand:
                x, y = random.choice([config.CYCLE_BACK_LEFT, config.CYCLE_BACK_RIGHT])
                logger.info("CYCLE: %s at back (%d,%d) [elixir=%d]", card_name, x, y, scene.elixir)
                return Action(slot=hand[card_name], x=x, y=y)

        return None
