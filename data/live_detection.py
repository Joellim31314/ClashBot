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
import torchvision
_orig = torch.load
def _patched(*a, **kw):
    kw.setdefault("weights_only", False)
    return _orig(*a, **kw)
torch.load = _patched

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

# Arena crop for 1080x2400
ARENA_CROP = (0.020, 0.070, 0.960, 0.690)
YOLO_SIZE  = (576, 896)
NMS_IOU_THRESHOLD = 0.6  # cross-detector NMS (matches KataCR ComboDetector)

# Font for PIL rendering (bundled with KataCR vendor)
FONT_PATH = str(Path(__file__).resolve().parent.parent / "vendor" / "KataCR"
                / "katacr" / "utils" / "fonts" / "Consolas.ttf")

UI_CLASSES = {
    "tower-bar", "bar", "bar-level", "elixir", "emote", "clock",
    "padding_belong", "evolution-symbol", "ice-spirit-evolution-symbol",
    "skeleton-king-bar", "selected", "text", "king-tower-bar",
    "dagger-duchess-tower-bar",
}
TOWER_CLASSES = {"king-tower", "queen-tower", "cannoneer-tower", "dagger-duchess-tower"}

COL_BRIDGE = (255, 200, 0)  # BGR — bridge line (drawn via cv2)

# ---------------------------------------------------------------------------
# Rendering utilities (ported from KataCR — can't import due to JAX dep)
# ---------------------------------------------------------------------------

_font_cache: dict[int, ImageFont.FreeTypeFont] = {}


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    if size not in _font_cache:
        try:
            _font_cache[size] = ImageFont.truetype(FONT_PATH, size)
        except OSError:
            _font_cache[size] = ImageFont.load_default(size=size)
    return _font_cache[size]


def get_box_colors(n: int) -> list[tuple[int, int, int]]:
    """Return *n* visually distinct RGB colours from matplotlib's BRG colourmap."""
    cmap = plt.cm.brg
    step = max(1, cmap.N // n)
    colors = cmap([i for i in range(0, cmap.N, step)])
    colors = (colors[:, :3] * 255).astype(int)
    return [tuple(c) for c in colors]


def build_label2colors(class_ids: np.ndarray) -> dict[int, tuple[int, int, int]]:
    """Map unique class IDs → distinct RGB colours."""
    if not len(class_ids):
        return {}
    labels = np.unique(class_ids).astype(np.int32)
    colors = get_box_colors(len(labels))
    return dict(zip(labels.tolist(), colors))


def plot_box_PIL(
    image: Image.Image,
    box_xyxy: tuple[int, int, int, int],
    text: str = "",
    fontsize: int = 14,
    box_color: tuple[int, int, int] = (255, 0, 0),
    alpha: int = 150,
) -> Image.Image:
    """Draw a bounding box + label on an RGBA overlay image."""
    draw = ImageDraw.Draw(image)
    x1, y1, x2, y2 = int(box_xyxy[0]), int(box_xyxy[1]), int(box_xyxy[2]), int(box_xyxy[3])
    rgba = tuple(box_color) + (alpha,)
    draw.rectangle([x1, y1, x2, y2], outline=rgba, width=2)

    font = _load_font(fontsize)
    bbox = font.getbbox(text)
    w_text, h_text = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x_text = x1
    y_text = y1 - h_text - 4 if y1 > h_text + 4 else y1
    draw.rounded_rectangle(
        [x_text, y_text, x_text + w_text + 4, y_text + h_text + 4],
        radius=2, fill=rgba,
    )
    draw.text((x_text + 2, y_text + 1), text, fill=(255, 255, 255), font=font)
    return image


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

    # --- PIL RGBA overlay for detection annotations ---
    if detections:
        unique_classes = sorted(set(d[0] for d in detections))
        cls_name_to_id = {name: i for i, name in enumerate(unique_classes)}
        cls_ids = np.array([cls_name_to_id[d[0]] for d in detections])
        label2color = build_label2colors(cls_ids)
    else:
        cls_name_to_id = {}
        label2color = {}

    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))

    side_tags = {"enemy": "E", "friendly": "F", "tower": "T"}
    for cls_name, conf, x1, y1, x2, y2, side in detections:
        cls_id = cls_name_to_id[cls_name]
        color = label2color[cls_id]
        label = f"{cls_name} {conf:.2f} [{side_tags[side]}]"
        overlay = plot_box_PIL(overlay, (x1, y1, x2, y2), text=label,
                               fontsize=14, box_color=color, alpha=150)

    composited = Image.alpha_composite(base, overlay).convert("RGB")
    frame = cv2.cvtColor(np.array(composited), cv2.COLOR_RGB2BGR)

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
