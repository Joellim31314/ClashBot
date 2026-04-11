# ClashBot — AI Agent Context

## What Is This Project?

An automated Clash Royale bot that plays the game via an Android emulator (LDPlayer 9) controlled through ADB. Uses Computer Vision (YOLO) for perception and a layered decision engine (heuristics → imitation learning → RL) for strategy.

**Owner:** Joel Lim
**Platform:** Windows 11, RTX 4050 laptop
**Language:** Python 3.11+
**Target:** 3k → 5k → 10k trophies (incremental)

## Architecture

```
Screen Capture (ADB) → Object Detection (YOLO/pixel) → State Representation → Decision Engine → Action Execution (ADB tap/swipe)
```

The bot runs Clash Royale inside LDPlayer 9 at **1080x2400** resolution (DPI 320). All screen coordinates are calibrated to this resolution.

## Project Structure

```
ClashBot/
├── CLAUDE.md                  # THIS FILE — project context for AI agents
├── CLASHBOT_MASTER.md         # Full project plan, research, and roadmap
├── docs/plans/                # Implementation plans (phase breakdowns)
├── requirements.txt           # Python dependencies
├── config.py                  # Screen coordinates, emulator settings, constants
├── main.py                    # Entry point — runs the bot loop
├── bot/
│   ├── __init__.py
│   ├── models.py              # Shared dataclasses (Detection, BattleScene, Action, etc.)
│   ├── screen.py              # ADB screen capture (ScreenCapture class)
│   ├── actions.py             # ADB tap/swipe actions (ActionExecutor class)
│   ├── state.py               # Game state detection + BattleScene builder
│   ├── strategy.py            # Decision engine (Phase 1 = random cards)
│   └── vision.py              # YOLODetector + CardMatcher (Phase 2)
├── data/
│   ├── test_pretrained.py     # Evaluate KataCR model on screenshots
│   ├── capture_templates.py   # Capture card templates from emulator
│   ├── generate_training_data.py  # Synthetic YOLO training data
│   ├── train_yolo.py          # Fine-tune/train YOLOv8
│   └── dataset.yaml           # YOLO dataset config
├── models/                    # YOLO weights (gitignored)
│   └── katacr/                # KataCR pre-trained weights
└── tests/
    ├── test_screen.py, test_actions.py, test_state.py
    ├── test_strategy.py, test_pipeline.py
    ├── test_models.py         # Dataclass tests
    └── test_vision.py         # Vision module tests
```

## Key Technical Details

- **Emulator:** LDPlayer 9 with ADB enabled on local connection
- **Resolution:** 1080x2400 (DPI 320) — ALL coordinates depend on this. Matches KataCR's pre-trained model.
- **ADB library:** `pure-python-adb` (no adb binary needed)
- **Screen capture:** `adb exec-out screencap -p` → ~100-200ms per frame (5-10 FPS)
- **Actions:** `adb shell input tap X Y` and `adb shell input swipe X1 Y1 X2 Y2`
- **State detection:** Pixel color analysis for game state + optional YOLO for arena objects
- **Vision (Phase 2):** YOLOv8 (KataCR dual-detector) for troops/buildings, template matching for cards
- **Strategy (Phase 1):** Random card placement when elixir >= card cost

## Development Phases

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 1 | Foundation — ADB pipeline, random bot | **Complete** |
| **Phase 2** | YOLO vision — troop/card detection | **Current** (code done, testing model) |
| Phase 3 | Heuristic bot — rules engine | Planned |
| Phase 4 | Expanded vision — all game objects | Planned |
| Phase 5 | Learning — imitation + RL | Planned |
| Phase 6 | Optimization — advanced tactics | Planned |

## Coding Conventions

- **Python 3.11+**, type hints on all public functions
- Classes for major components: `ScreenCapture`, `ActionExecutor`, `GameStateDetector`, `Strategy`
- `config.py` holds ALL magic numbers (coordinates, thresholds, timings)
- No hardcoded coordinates in module files — always import from `config.py`
- Use `logging` module, not `print()` for debug output
- Tests use `pytest` with descriptive test names
- Incremental approach — get it working first, optimize later

## Important Constraints

- All coordinates are for **1080x2400 LDPlayer 9** (DPI 320) — do not change resolution assumptions
- ADB connection assumes local emulator (localhost, default port)
- Bot must handle menu navigation (click Battle, dismiss results) not just in-battle play
- Human-like random delays between actions (50-200ms jitter) to reduce detection risk
- Phase 1 bot will lose every game — that's expected. Pipeline correctness is the goal.

## Reference Documents

- `CLASHBOT_MASTER.md` — Full research, architecture, ML concepts, and master checklist
- `docs/plans/` — Phase-specific implementation plans with task breakdowns
