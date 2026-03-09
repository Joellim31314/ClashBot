# ClashBot — Master Project Document
> Last updated: 2026-03-08 | Status: Phase 1 in progress

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Your Setup & Goals](#2-your-setup--goals)
3. [How Existing Bots Work](#3-how-existing-bots-work)
4. [Screen Control — The Foundation](#4-screen-control--the-foundation)
5. [Computer Vision — Seeing the Game](#5-computer-vision--seeing-the-game)
6. [Decision Making — The Brain](#6-decision-making--the-brain)
7. [Game Knowledge Database](#7-game-knowledge-database)
8. [Potential Blockers & Challenges](#8-potential-blockers--challenges)
9. [Key ML Concepts Clarified](#9-key-ml-concepts-clarified)
10. [System Architecture](#10-system-architecture)
11. [Long-Term Roadmap](#11-long-term-roadmap)
12. [Phase 1 Implementation Plan](#12-phase-1-implementation-plan)
13. [Master Task Checklist](#13-master-task-checklist)

---

## 1. Project Overview

Building a Clash Royale bot that can play better than most humans is **ambitious but achievable**. Several open-source projects have already demonstrated bots that can beat training camp AI, and some are pushing toward competitive ladder play.

The approach is a **hybrid of Computer Vision (YOLO) + Heuristic Rules + Reinforcement Learning**, running on an Android emulator controlled via ADB. We build incrementally — a dumb bot first, then make it progressively smarter.

**Trophy targets**: 3k → 5k → 10k (long term)

---

## 2. Your Setup & Goals

| Item | Detail |
|---|---|
| **Platform** | Windows laptop (desktop emulator, not phone) |
| **GPU** | RTX 4050 — excellent for YOLO training + inference |
| **Emulator** | LDPlayer 9 (to be installed) |
| **Account** | Throwaway/alt account (ban risk accepted) |
| **ML background** | ETL pipelines, logistic regression, random forests |
| **Approach** | Incremental — working dumb bot first, then iterate |
| **Primary language** | Python |

---

## 3. How Existing Bots Work

### Notable Open-Source Projects

| Project | Approach | Level Achieved | Key Tech |
|---|---|---|---|
| [ClashRoyaleBuildABot](https://github.com/Pbatch/ClashRoyaleBuildABot) | YOLOv5 state detection + rule-based decisions | Beats training camp, playable in ladder | Python, YOLOv5, ADB, emulator |
| [Imtinan1996 DL Bot](https://github.com/Imtinan1996/Clash-Royale-Bot-using-Deep-Learning-technologies) | DL to emulate top player styles from RoyaleTV | Beats training camp AI | Deep learning, emulator |
| [CRBot](https://github.com/krazyness/CRBot-public) | ML + RL agent with PyTorch | Learning through self-play | PyTorch, Roboflow, BlueStacks |
| [py-clash-bot](https://github.com/pyclashbot/py-clash-bot) | Image recognition for farming automation | Task automation only | Image recognition, emulator |
| [OpenCVClashRoyale](https://github.com/WilliamUW/OpenCVClashRoyale) | OpenCV + Sikuli for 2v2 | Prototype | OpenCV, Sikuli, Python |

### Common Architecture Pattern

All successful bots follow this pipeline:

```
Screen Capture → Object Detection → State Representation → Decision Engine → Action Execution
     (ADB)          (YOLO/OpenCV)      (structured data)    (rules/RL/DL)      (ADB tap/swipe)
```

---

## 4. Screen Control — The Foundation

### How it works
Bots run Clash Royale on an **Android emulator** (LDPlayer 9) and control it via **ADB (Android Debug Bridge)**:

- **Screen capture**: `adb exec-out screencap -p` → PNG image
- **Tap**: `adb shell input tap X Y` → simulates finger tap
- **Swipe**: `adb shell input swipe X1 Y1 X2 Y2` → drag gesture

### Python Libraries
- `pure-python-adb` — most popular, works without adb binary
- `adb-pywrapper` — clean Python wrapper
- `scrcpy` — screen mirroring tool, good for debugging

### Latency
ADB screenshot capture takes **~100-200ms per frame** (~5-10 FPS). This is acceptable for Clash Royale since it's strategy-paced, not twitch-based.

---

## 5. Computer Vision — Seeing the Game

### What Needs to Be Detected

| Element | Method | Difficulty |
|---|---|---|
| Cards in hand | Template matching / YOLO | Easy |
| Elixir count | Pixel color analysis | Easy |
| Friendly & enemy troops | YOLO | Medium–Hard |
| Tower HP bars | Pixel analysis / YOLO | Medium |
| Troop positions on arena | YOLO + coordinate mapping | Medium |
| Spells in flight | YOLO | Hard |
| Enemy card cycle | Inference from observations | Very Hard |

### Why YOLO ✅

- **YOLOv8** detects multiple objects per frame at **30+ FPS on GPU**
- Pre-trained Clash Royale datasets exist on [Roboflow Universe](https://universe.roboflow.com/)
- **Transfer learning** gets you a working detector with only **200–500 annotated images**
- Your RTX 4050 handles real-time YOLO inference easily

### Using YouTube Videos as Training Data ✅

This is a great approach and is widely used:

1. **Download** gameplay using `yt-dlp`
2. **Extract frames** at ~1/sec intervals using OpenCV
3. **Annotate** bounding boxes in [Roboflow](https://roboflow.com) (free tier works)
4. **Augment** (rotations, brightness, crops) to multiply the dataset

> **Tip**: Start from an existing Roboflow CR dataset, supplement with YouTube data. A few days of annotation = a working detector.

**Key caveats:**
- Standardize to emulator resolution (720×1280)
- Include diverse skins/card levels in training data
- Small elements (elixir dots) may need cropped close-up images

---

## 6. Decision Making — The Brain

### Three Layers (Build in Order)

#### Layer 1: Hard-Coded Heuristics (Day 1 — never needs to be learned)

| Rule | How |
|---|---|
| Goal = destroy enemy towers | Hard-coded reward signal |
| Don't play if elixir < card cost | Elixir tracking script |
| Defend when enemy crosses bridge | Position-based trigger zone |
| Don't ignore a push | YOLO proximity check |
| Don't overcommit elixir | Threshold heuristic |
| Ranged troops go behind tanks | Card property lookup |
| Track enemy cards played | Card tracking system |

#### Layer 2: Scripted Assistants (Phase 2–3)

- **Elixir Counter** — Pixel color thresholds on the elixir bar. No ML needed.
- **Enemy Card Tracker** — Log each card the enemy plays. After 8 unique cards = full deck known, predict cycle.
- **Threat Assessment** — Total DPS of enemy troops crossing the bridge.
- **Tower HP Monitor** — Read HP bar pixel values to detect low HP towers.

#### Layer 3: Learned Strategy (Phase 5+)

- **Imitation Learning**: Neural net trained on pro replay footage predicts "what would a top player do here?"
- **Reinforcement Learning**: Bot plays real games, optimises for tower damage, crowns, win rate. Heuristics give it a massive head start so it doesn't learn from total ignorance.

---

## 7. Game Knowledge Database

Encode card properties as data — **don't make the model learn** what a Hog Rider does:

```python
CARDS = {
    "hog_rider": {
        "elixir": 4, "type": "win_condition", "speed": "very_fast",
        "targets": "buildings", "hp": 1408, "dps": 176,
        "counters": ["cannon", "tesla", "mini_pekka", "skeleton_army"],
        "role": "offense"
    },
    "skeleton_army": {
        "elixir": 3, "type": "swarm", "count": 15,
        "counters": ["arrows", "log", "valkyrie"],
        "role": "defense", "weak_to_splash": True
    },
    # 100+ cards...
}
```

Full data available from the [Clash Royale API](https://developer.clashroyale.com/) and fan wikis like [statsroyale.com](https://statsroyale.com).

---

## 8. Potential Blockers & Challenges

### 🔴 Critical

| Blocker | Impact | Mitigation |
|---|---|---|
| **Account ban risk** | Supercell TOS prohibits bots | Alt account only, never main |
| **Game updates break visuals** | YOLO model breaks on patch day | Retrain after updates; robust augmentation |
| **ADB latency** | 5–10 FPS limit | Acceptable for CR; use `scrcpy` to optimise |
| **No simulation environment** | Can't do self-play at 1000× speed like chess engines | Must play real-time; limits training throughput |

### 🟡 Significant

| Challenge | Notes |
|---|---|
| **Imperfect information** | Enemy hand and elixir invisible — must infer |
| **Real-time decisions** | <1 second per action |
| **Vast action space** | 100+ cards × arena positions = enormous |
| **Opponent adaptation** | Humans adjust mid-game |
| **Troop identification** | Small, overlapping sprites |

### 🟢 Manageable

| Issue | Solution |
|---|---|
| Elixir counting | Pixel color, very reliable |
| Card recognition in hand | Template matching, very reliable |
| Tower HP | Pixel-based |
| Menu navigation | Fixed UI coordinates |

---

## 9. Key ML Concepts Clarified

1. **Deep Learning vs Reinforcement Learning** — Different things. DL = neural nets learning patterns from data (YOLO detecting troops). RL = agent learning by trial-and-error with rewards. You'll use **both** — DL for perception, RL for strategy.

2. **Don't make a model learn the rules** — The game rules (what each card does, what winning means) should be **hard-coded as heuristics**, not learned. Only strategy (when/where to play which card) needs to be learned.

3. **YouTube data = vision + imitation, not RL** — YouTube footage trains the YOLO vision model and the imitation learning model. Reinforcement learning requires the bot to actually play games and receive live rewards — you can't RL-train from video.

4. **YOLO ≠ decision maker** — YOLO handles **perception** (what is on screen). A separate system handles **decision-making** (what action to take). These are completely independent.

---

## 10. System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      CLASH ROYALE BOT                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────┐    ┌─────────────────────────────────┐   │
│  │  LDPlayer 9   │───▶│  Screen Capture (ADB)           │   │
│  │  Emulator     │    └───────────────┬─────────────────┘   │
│  └──────────────┘                    │                      │
│                                      ▼                      │
│                         ┌────────────────────────┐         │
│                         │  YOLO Object Detector   │         │
│                         │  (troops, towers, cards)│         │
│                         └────────────┬───────────┘         │
│                                      │                      │
│                                      ▼                      │
│                         ┌────────────────────────┐         │
│                         │  State Generator        │         │
│                         │  - Elixir counter       │         │
│                         │  - Enemy card tracker   │         │
│                         │  - Tower HP monitor     │         │
│                         │  - Troop positions      │         │
│                         └────────────┬───────────┘         │
│                                      │                      │
│                                      ▼                      │
│                         ┌────────────────────────┐         │
│                         │  Decision Engine        │         │
│                         │  Phase 1: Random        │         │
│                         │  Phase 3: Heuristics    │         │
│                         │  Phase 5: Imitation+RL  │         │
│                         └────────────┬───────────┘         │
│                                      │                      │
│                                      ▼                      │
│                         ┌────────────────────────┐         │
│                         │  Action Executor        │         │
│                         │  (ADB tap/swipe at X,Y) │         │
│                         └────────────────────────┘         │
└────────────────────────────────────────────────────────────┘
```

---

## 11. Long-Term Roadmap

### Phase 1: Foundation (Weeks 1–3)
Get a working pipeline. Bot is dumb — plays random cards — but the full system is wired up.

### Phase 2: Vision (Weeks 4–7)
YOLO-powered object detection. Bot can now "see" troops, towers, and cards in hand.

### Phase 3: Heuristic Bot (Weeks 8–11)
Rules engine. Bot knows card counters, elixir management, threat assessment.
**Goal: Beat training camp AI consistently.**

### Phase 4: Smarter Vision (Weeks 12–15)
Expand YOLO to cover all game objects. Add troop tracking across frames, HP detection.

### Phase 5: Learning (Weeks 16–24)
Imitation learning from pro replays + reinforcement learning from live matches.
**Goal: Beat average human players.**

### Phase 6: Optimization (Weeks 24+)
Matchup-specific strategies, advanced tactics (cycling, split push, pump management).
**Goal: 3k → 5k → 10k trophies.**

---

## 12. Phase 1 Implementation Plan

### Manual Setup (You Do This First)

> **Required before writing any code:**
> 1. Install **LDPlayer 9** → [ldplayer.net](https://www.ldplayer.net/)
> 2. Install **Clash Royale** inside LDPlayer from Play Store
> 3. Create a **new throwaway Supercell account** and finish the tutorial
> 4. Set emulator resolution to **720×1280** in LDPlayer display settings
> 5. Enable **ADB**: LDPlayer Settings → Other → ADB debugging → Open local connection
> 6. Install **Android Platform Tools** and add `adb.exe` to your system PATH

### Project Structure

```
ClashBot/
├── requirements.txt      # Python dependencies
├── config.py             # Screen coordinates, emulator settings
├── main.py               # Entry point — runs the bot loop
├── bot/
│   ├── __init__.py
│   ├── screen.py         # ADB screen capture
│   ├── actions.py        # ADB tap/swipe actions
│   ├── state.py          # Pixel-based game state detection
│   └── strategy.py       # Decision engine (Phase 1 = random)
└── tests/
    └── test_pipeline.py  # Verify everything connects
```

### Files to Build

| File | What it does |
|---|---|
| `requirements.txt` | `pure-python-adb`, `Pillow`, `numpy`, `opencv-python` |
| `config.py` | All hardcoded coordinates (card slots, arena grid, UI) for 720×1280 |
| `bot/screen.py` | `ScreenCapture` class — connects ADB, `capture()` returns PIL image |
| `bot/actions.py` | `ActionExecutor` class — `tap(x,y)`, `play_card(slot, x, y)`, human-like delays |
| `bot/state.py` | Pixel-color-based: `is_in_battle()`, `is_in_menu()`, `get_elixir_count()` |
| `bot/strategy.py` | Waits for elixir ≥ 7, picks random card + random bridge-biased position |
| `main.py` | Loop: capture → detect state → if battle run strategy → if menu click battle |

> **Coordinate warning**: All coordinates are specific to **720×1280 in LDPlayer 9**. Wrong resolution = every tap misses.

### Main Game Loop Logic

```
while True:
    screen = capture()
    state  = detect(screen)

    if state == BATTLE:
        action = strategy.decide(state)
        executor.play_card(action)

    elif state == MENU:
        executor.tap(BATTLE_BUTTON)

    elif state == GAME_OVER:
        sleep(3)
        executor.tap(OK_BUTTON)
```

### Verification Tests

```bash
# Test 1: ADB connection
python -c "from bot.screen import ScreenCapture; sc = ScreenCapture(); print('Connected:', sc.is_connected())"

# Test 2: Screen capture
python -c "from bot.screen import ScreenCapture; sc = ScreenCapture(); sc.capture().save('screenshot.png'); print('Saved')"

# Test 3: Tap action (taps center of emulator)
python -c "from bot.actions import ActionExecutor; ActionExecutor().tap(360, 640)"

# Test 4: Elixir reading (run during a battle)
python -c "from bot.screen import ScreenCapture; from bot.state import GameStateDetector; print('Elixir:', GameStateDetector(ScreenCapture()).get_elixir_count())"
```

**Success criteria**: Run `python main.py`, watch the bot click Battle, enter a game, and play cards (badly). It will lose. That's fine — the pipeline works.

---

## 13. Master Task Checklist

### Phase 1: Foundation ← Current
- [x] Research existing bots and approaches
- [x] Define architecture and roadmap
- [ ] Install LDPlayer 9 + Clash Royale + throwaway account
- [ ] Set up Python venv + install dependencies
- [ ] Build `bot/screen.py` — ADB screen capture
- [ ] Build `bot/actions.py` — ADB tap/swipe executor
- [ ] Build `bot/state.py` — pixel-based game state detection
- [ ] Build `bot/strategy.py` — random card strategy
- [ ] Build `main.py` — main game loop
- [ ] Verify end-to-end pipeline works (capture → decide → act)

### Phase 2: Vision
- [ ] Download YouTube gameplay clips (`yt-dlp`)
- [ ] Extract frames with OpenCV
- [ ] Annotate with Roboflow (cards in hand, towers first)
- [ ] Fine-tune YOLOv8 on custom dataset
- [ ] Build pixel-based elixir counter
- [ ] Integrate YOLO detections into state generator

### Phase 3: Heuristic Bot
- [ ] Build card knowledge database (counters, elixir, roles)
- [ ] Implement bridge-cross defense trigger
- [ ] Implement enemy card tracking (cycle prediction)
- [ ] Implement threat DPS assessment
- [ ] Implement elixir management (reserve threshold)
- [ ] **Goal: Beat training camp AI consistently**

### Phase 4: Smarter Vision
- [ ] Expand YOLO to all troops, spells, buildings
- [ ] Add frame-to-frame troop tracking
- [ ] Add tower HP bar detection
- [ ] Retrain with more diverse YouTube data

### Phase 5: Learning
- [ ] Imitation learning from pro replay data
- [ ] Define RL state/action/reward schema
- [ ] Implement RL training loop (PPO or DQN)
- [ ] Run bot through hundreds of games for self-improvement
- [ ] **Goal: Beat average human players**

### Phase 6: Optimization
- [ ] Recognise enemy deck archetypes, adapt strategy
- [ ] Add advanced tactics (split push, pump play, cycling)
- [ ] Speed optimisation for faster reactions
- [ ] **Goal: 3k → 5k → 10k trophies**
