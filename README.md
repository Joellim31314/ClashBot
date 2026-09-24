# ClashBot

An autonomous Clash Royale bot built around the **Hog 2.6** deck. It plays inside an Android emulator (LDPlayer 9), using computer vision to read the game and a rule-based engine to decide what to play. Built as a hands-on ML/AI learning project.

## How it works

```
Screen capture (ADB) -> Detection (YOLO + pixel analysis) -> Game state -> Strategy -> Action (ADB tap/swipe)
```

- **Emulator control:** frames are captured and taps/swipes sent over ADB (`pure-python-adb`), with randomized human-like delays.
- **State detection:** pixel-color checks classify the screen (menu, battle, game over, trophy road) and read the elixir bar.
- **Vision:** pre-trained [KataCR](https://github.com/wty-yy/KataCR) dual YOLOv8 detectors find troops and buildings; OpenCV template matching identifies the cards in hand.
- **Strategy:** `HogStrategy` follows a defend -> attack -> cycle priority using elixir, hand and detections. A random-play baseline is also included.
- **Menu automation:** the bot queues battles and dismisses result and chest screens on its own.

## Project layout

```
main.py        Entry point / bot loop
config.py      Coordinates, thresholds, deck definition
bot/           Screen capture, actions, state, vision, strategy, models
data/          Live detection overlay, template capture, YOLO training tools
tests/         pytest suites
```

## Setup

Requires Python 3.11+ and LDPlayer 9 configured to **1080x2400, DPI 320** with ADB enabled. All coordinates in `config.py` assume this resolution.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Optional: place KataCR weights in `models/katacr/` and card templates in `data/card_templates/` to enable vision. Without them the bot falls back to a non-vision mode.

## Run

```bash
python main.py          # start the bot
python -m pytest tests  # run tests
```

## Status

The pipeline, vision integration and first-pass Hog 2.6 heuristics are implemented. The strategy has not been benchmarked, and the planned replay-based imitation learning and RL phases were not started. The project is currently on hold.

## Disclaimer

For educational purposes only. Automating the game may violate its terms of service; use at your own risk.
