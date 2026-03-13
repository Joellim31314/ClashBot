"""Shared data models for ClashBot."""
from dataclasses import dataclass, field


@dataclass
class Detection:
    class_name: str                    # e.g. "knight", "hog_rider"
    confidence: float                  # 0.0-1.0
    bbox: tuple[int, int, int, int]    # (x1, y1, x2, y2)
    center: tuple[int, int]            # (cx, cy)
    side: str                          # "friendly" | "enemy" | "unknown"


@dataclass
class CardInHand:
    slot: int          # 0-3
    card_name: str     # e.g. "hog_rider", "unknown"
    confidence: float


@dataclass
class BattleScene:
    detections: list[Detection] = field(default_factory=list)
    cards_in_hand: list[CardInHand] = field(default_factory=list)
    elixir: int = 0
    timestamp: float = 0.0


@dataclass
class Action:
    slot: int  # Card slot 0-3
    x: int     # Arena X coordinate
    y: int     # Arena Y coordinate
