"""Live YOLO detection overlay — streams annotated frames from the emulator.

Shows a window with bounding boxes drawn on the live game.
Press Q to quit, S to save a screenshot of the current frame.

Usage:
    python data/live_detection.py [--conf 0.35] [--scale 0.5]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vendor" / "KataCR"))

import torch
_orig = torch.load
def _patched(*a, **kw):
    kw.setdefault("weights_only", False)
    return _orig(*a, **kw)
torch.load = _patched

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

# Arena crop for 1080x2400
ARENA_CROP = (0.020, 0.070, 0.960, 0.690)
YOLO_SIZE  = (576, 896)

UI_CLASSES = {
    "tower-bar", "bar", "bar-level", "elixir", "emote", "clock",
    "padding_belong", "evolution-symbol", "ice-spirit-evolution-symbol",
    "skeleton-king-bar", "selected", "text", "king-tower-bar",
    "dagger-duchess-tower-bar",
}
TOWER_CLASSES = {"king-tower", "queen-tower", "cannoneer-tower", "dagger-duchess-tower"}

# BGR colours for OpenCV
COL_ENEMY    = (60,  60, 255)   # red
COL_FRIENDLY = (60, 200,  60)   # green
COL_TOWER    = (0,  200, 255)   # yellow
COL_BRIDGE   = (255, 200,   0)  # cyan — bridge line


def load_models():
    print("Loading KataCR detectors...")
    m1 = YOLO("models/katacr/detector1_v0.7.13.pt")
    m2 = YOLO("models/katacr/detector2_v0.7.13.pt")
    print(f"  detector1: {len(m1.names)} classes")
    print(f"  detector2: {len(m2.names)} classes")
    return m1, m2


def run_detection(models, img: Image.Image, conf: float):
    iw, ih = img.size
    ax1 = round(ARENA_CROP[0] * iw)
    ay1 = round(ARENA_CROP[1] * ih)
    ax2 = round((ARENA_CROP[0] + ARENA_CROP[2]) * iw)
    ay2 = round((ARENA_CROP[1] + ARENA_CROP[3]) * ih)
    arena = img.crop((ax1, ay1, ax2, ay2)).resize(YOLO_SIZE, Image.LANCZOS)
    sx = (ax2 - ax1) / YOLO_SIZE[0]
    sy = (ay2 - ay1) / YOLO_SIZE[1]

    results = []
    seen = []
    for model in models:
        for box in model.predict(source=arena, conf=conf, iou=0.45, verbose=False)[0].boxes:
            cls = model.names[int(box.cls[0])]
            if cls in UI_CLASSES:
                continue
            bconf = float(box.conf[0])
            cx1, cy1, cx2, cy2 = box.xyxy[0].tolist()
            x1 = int(cx1 * sx) + ax1
            y1 = int(cy1 * sy) + ay1
            x2 = int(cx2 * sx) + ax1
            y2 = int(cy2 * sy) + ay1
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            # deduplicate
            if any(abs(cx - s[0]) < 30 and abs(cy - s[1]) < 30 for s in seen):
                continue
            seen.append((cx, cy))
            side = "tower" if cls in TOWER_CLASSES else ("enemy" if cy < ih * 0.52 else "friendly")
            results.append((cls, bconf, x1, y1, x2, y2, side))
    return results, (ax1, ay1, ax2, ay2)


def draw_frame(img: Image.Image, detections, arena_box, bridge_y_frac: float, scale: float):
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    ih, iw = frame.shape[:2]

    # Draw arena crop outline (grey)
    ax1, ay1, ax2, ay2 = arena_box
    cv2.rectangle(frame, (ax1, ay1), (ax2, ay2), (80, 80, 80), 1)

    # Draw bridge line
    by = int(bridge_y_frac * ih)
    cv2.line(frame, (0, by), (iw, by), COL_BRIDGE, 1)
    cv2.putText(frame, "bridge", (5, by - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COL_BRIDGE, 1)

    for cls, conf, x1, y1, x2, y2, side in detections:
        col = COL_TOWER if side == "tower" else (COL_ENEMY if side == "enemy" else COL_FRIENDLY)
        cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
        label = f"{cls} {conf:.0%}"
        (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(frame, (x1, y1 - lh - 6), (x1 + lw + 4, y1), col, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)

    if scale != 1.0:
        frame = cv2.resize(frame, (int(iw * scale), int(ih * scale)))
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf",  type=float, default=0.35, help="Confidence threshold")
    parser.add_argument("--scale", type=float, default=0.4,  help="Display scale (0.4 = 40%% of original)")
    args = parser.parse_args()

    import config
    from bot.screen import ScreenCapture

    models = load_models()

    print("Connecting to emulator...")
    screen = ScreenCapture()
    if not screen.is_connected():
        print("ERROR: Cannot connect to emulator. Is LDPlayer running?")
        sys.exit(1)
    print("Connected. Press Q to quit, S to save frame.\n")

    save_dir = Path("data/live_saves")
    save_dir.mkdir(exist_ok=True)

    cv2.namedWindow("ClashBot Live Detection", cv2.WINDOW_NORMAL)
    bridge_y_frac = config.ARENA_BRIDGE_Y / config.SCREEN_HEIGHT

    frame_times = []
    save_count = 0

    while True:
        t0 = time.time()

        # Capture
        try:
            img = screen.capture()
        except Exception as e:
            print(f"Capture error: {e}")
            time.sleep(0.5)
            continue

        # Detect
        detections, arena_box = run_detection(models, img, args.conf)

        # Draw
        t_detect = time.time()
        frame = draw_frame(img, detections, arena_box, bridge_y_frac, args.scale)

        # FPS overlay
        frame_times.append(time.time() - t0)
        if len(frame_times) > 20:
            frame_times.pop(0)
        fps = 1.0 / (sum(frame_times) / len(frame_times))
        detect_ms = (t_detect - t0) * 1000

        n_troops = sum(1 for d in detections if d[6] != "tower")
        n_towers = sum(1 for d in detections if d[6] == "tower")
        status = (f"FPS: {fps:.1f}  |  detect: {detect_ms:.0f}ms  |  "
                  f"troops: {n_troops}  towers: {n_towers}  |  conf>={args.conf:.0%}  |  Q=quit  S=save")
        cv2.putText(frame, status, (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.imshow("ClashBot Live Detection", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            save_path = save_dir / f"live_{save_count:04d}.png"
            img.save(save_path)
            print(f"Saved: {save_path}  ({len(detections)} detections)")
            save_count += 1

    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
