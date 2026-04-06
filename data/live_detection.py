"""Live YOLO detection overlay — streams annotated frames from the emulator.

Shows a window with bounding boxes drawn on the live game.
Press Q to quit, S to save a screenshot of the current frame.

Usage:
    python data/live_detection.py [--conf 0.35] [--scale 0]
"""
import argparse
import sys
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vendor" / "KataCR"))

import torch
import torchvision
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
NMS_IOU_THRESHOLD = 0.6  # cross-detector NMS (matches KataCR ComboDetector)

UI_CLASSES = {
    "tower-bar", "bar", "bar-level", "elixir", "emote", "clock",
    "padding_belong", "evolution-symbol", "ice-spirit-evolution-symbol",
    "skeleton-king-bar", "selected", "text", "king-tower-bar",
    "dagger-duchess-tower-bar",
}
TOWER_CLASSES = {"king-tower", "queen-tower", "cannoneer-tower", "dagger-duchess-tower"}

COL_BRIDGE = (255, 200, 0)  # BGR bridge line (drawn via cv2)

_CLASS_COLOR_CACHE: dict[str, tuple[int, int, int]] = {}


def _class_color_bgr(class_name: str) -> tuple[int, int, int]:
    """Stable class-to-colour mapping for cv2 overlays."""
    cached = _CLASS_COLOR_CACHE.get(class_name)
    if cached is not None:
        return cached

    seed = zlib.crc32(class_name.encode("utf-8")) & 0xFFFFFFFF
    hue = seed % 180
    sat = 190 + ((seed >> 8) % 66)   # 190..255
    val = 200 + ((seed >> 16) % 56)  # 200..255
    hsv = np.uint8([[[hue, sat, val]]])
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]
    color = (int(bgr[0]), int(bgr[1]), int(bgr[2]))
    _CLASS_COLOR_CACHE[class_name] = color
    return color


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

    # Collect raw boxes from both detectors
    all_boxes: list[torch.Tensor] = []   # each [x1, y1, x2, y2, conf]  (crop space)
    all_classes: list[str] = []

    for model in models:
        result = model.predict(source=arena, conf=conf, iou=0.45, verbose=False)[0]
        for box in result.boxes:
            cls_name = model.names[int(box.cls[0])]
            if cls_name in UI_CLASSES:
                continue
            xyxy = box.xyxy[0]                      # [x1, y1, x2, y2]
            c = box.conf[0].unsqueeze(0)             # [conf]
            all_boxes.append(torch.cat([xyxy, c]))   # [x1, y1, x2, y2, conf]
            all_classes.append(cls_name)

    if not all_boxes:
        return [], (ax1, ay1, ax2, ay2)

    preds = torch.stack(all_boxes)  # [N, 5]
    # Cross-detector NMS (matches KataCR ComboDetector)
    keep = torchvision.ops.nms(preds[:, :4], preds[:, 4], iou_threshold=NMS_IOU_THRESHOLD)
    preds = preds[keep]
    all_classes = [all_classes[i] for i in keep.tolist()]

    # Translate to full-screen coordinates and classify side
    results = []
    for i, cls_name in enumerate(all_classes):
        cx1, cy1, cx2, cy2, bconf = preds[i].tolist()
        x1 = int(cx1 * sx) + ax1
        y1 = int(cy1 * sy) + ay1
        x2 = int(cx2 * sx) + ax1
        y2 = int(cy2 * sy) + ay1
        cy = (y1 + y2) // 2
        side = "tower" if cls_name in TOWER_CLASSES else ("enemy" if cy < ih * 0.52 else "friendly")
        results.append((cls_name, float(bconf), x1, y1, x2, y2, side))

    return results, (ax1, ay1, ax2, ay2)


def draw_frame(img: Image.Image, detections, arena_box, bridge_y_frac: float, scale: float):
    iw, ih = img.size
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    side_tags = {"enemy": "E", "friendly": "F", "tower": "T"}
    for cls_name, conf, x1, y1, x2, y2, side in detections:
        color = _class_color_bgr(cls_name)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        label = f"{cls_name} {conf:.2f} [{side_tags[side]}]"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.45
        thickness = 1
        (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        x_text = max(0, x1)
        y_bottom = y1 - 4
        if y_bottom - th - baseline - 4 < 0:
            y_bottom = min(ih - 1, y1 + th + baseline + 4)

        x_right = min(iw - 1, x_text + tw + 6)
        y_top = max(0, y_bottom - th - baseline - 4)
        cv2.rectangle(frame, (x_text, y_top), (x_right, y_bottom), color, -1)
        cv2.putText(frame, label, (x_text + 3, y_bottom - baseline - 2),
                    font, font_scale, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, label, (x_text + 3, y_bottom - baseline - 2),
                    font, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

    # --- cv2 diagnostic overlays (fully opaque) ---
    ax1, ay1, ax2, ay2 = arena_box
    cv2.rectangle(frame, (ax1, ay1), (ax2, ay2), (80, 80, 80), 1)

    by = int(bridge_y_frac * ih)
    cv2.line(frame, (0, by), (iw, by), COL_BRIDGE, 1)
    cv2.putText(frame, "bridge", (5, by - 5), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, COL_BRIDGE, 1, cv2.LINE_AA)

    if scale != 1.0:
        frame = cv2.resize(frame, (int(iw * scale), int(ih * scale)))
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf",  type=float, default=0.35, help="Confidence threshold")
    parser.add_argument("--scale", type=float, default=0.0,  help="Display scale (0 = auto-fit to screen)")
    args = parser.parse_args()

    import config
    from bot.screen import ScreenCapture

    if args.scale <= 0:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            monitor_h = user32.GetSystemMetrics(1)
            target_h = max(200, monitor_h - 100)
            args.scale = min(target_h / config.SCREEN_HEIGHT, 1.0)
        except Exception:
            args.scale = 0.6
        print(f"Auto-scale: {args.scale:.2f} "
              f"(window: {int(config.SCREEN_WIDTH * args.scale)}x"
              f"{int(config.SCREEN_HEIGHT * args.scale)})")
    else:
        args.scale = min(args.scale, 1.0)

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
    win_w = max(1, int(config.SCREEN_WIDTH * args.scale))
    win_h = max(1, int(config.SCREEN_HEIGHT * args.scale))
    cv2.resizeWindow("ClashBot Live Detection", win_w, win_h)
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

