# Task 3: Fix Display Window Size and Scale

## Problem
The live detection overlay window is too small to see anything useful. The `--scale` flag defaults to `0.4` (40%), so a 1080×2400 source renders as a tiny **432×960** window. Users need to either:
- Manually pass `--scale 0.7` every time, or
- Have the script auto-pick a reasonable size based on the monitor

## Goal
Make the display window default to a sensible, readable size — roughly fitting the screen height with some padding.

---

## Environment Context

| Item | Value |
|------|-------|
| **Source resolution** | 1080×2400 (very tall phone aspect ratio) |
| **Current default scale** | 0.4 (= 432×960 window — too small) |
| **File to modify** | `c:\Users\Joel Lim\Desktop\ClashBot\data\live_detection.py` |

---

## Current Code

### Argument parsing (line 210-214):
```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf",  type=float, default=0.35, help="Confidence threshold")
    parser.add_argument("--scale", type=float, default=0.4,  help="Display scale (0.4 = 40%% of original)")
    args = parser.parse_args()
```

### Window creation (line 231):
```python
cv2.namedWindow("ClashBot Live Detection", cv2.WINDOW_NORMAL)
```

### Frame scaling (line 205-207, inside `draw_frame()`):
```python
if scale != 1.0:
    frame = cv2.resize(frame, (int(iw * scale), int(ih * scale)))
return frame
```

---

## Required Changes

### Change 1: Auto-calculate scale from monitor height

Replace the fixed `default=0.4` with auto-detection. Add this logic near the top of `main()`, after parsing args:

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf",  type=float, default=0.35, help="Confidence threshold")
    parser.add_argument("--scale", type=float, default=0.0,  help="Display scale (0 = auto-fit to screen)")
    args = parser.parse_args()

    import config
    from bot.screen import ScreenCapture

    # Auto-calculate scale to fit monitor height (with padding)
    if args.scale <= 0:
        try:
            # Get primary monitor resolution
            import ctypes
            user32 = ctypes.windll.user32
            monitor_h = user32.GetSystemMetrics(1)  # SM_CYSCREEN = screen height
            # Leave 100px padding for taskbar + window title
            target_h = monitor_h - 100
            args.scale = target_h / config.SCREEN_HEIGHT
            args.scale = min(args.scale, 1.0)  # Never upscale
        except Exception:
            args.scale = 0.6  # Safe fallback
        print(f"Auto-scale: {args.scale:.2f} (window: {int(config.SCREEN_WIDTH * args.scale)}x{int(config.SCREEN_HEIGHT * args.scale)})")
```

### Change 2: Allow manual resize with WINDOW_NORMAL

The window is already created with `cv2.WINDOW_NORMAL` (line 231), which allows manual resize. No change needed here — this is already correct.

### Change 3: Optionally set initial window size explicitly

After `cv2.namedWindow`, add:
```python
cv2.namedWindow("ClashBot Live Detection", cv2.WINDOW_NORMAL)
win_w = int(config.SCREEN_WIDTH * args.scale)
win_h = int(config.SCREEN_HEIGHT * args.scale)
cv2.resizeWindow("ClashBot Live Detection", win_w, win_h)
```

This ensures the window opens at the correct size immediately.

---

## Full Modified `main()` Function

For reference, here is what the modified `main()` should look like (lines 210 onwards):

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf",  type=float, default=0.35, help="Confidence threshold")
    parser.add_argument("--scale", type=float, default=0.0,  help="Display scale (0 = auto-fit to screen)")
    args = parser.parse_args()

    import config
    from bot.screen import ScreenCapture

    # Auto-calculate scale to fit monitor height
    if args.scale <= 0:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            monitor_h = user32.GetSystemMetrics(1)
            target_h = monitor_h - 100
            args.scale = min(target_h / config.SCREEN_HEIGHT, 1.0)
        except Exception:
            args.scale = 0.6
        print(f"Auto-scale: {args.scale:.2f} "
              f"(window: {int(config.SCREEN_WIDTH * args.scale)}x"
              f"{int(config.SCREEN_HEIGHT * args.scale)})")

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
    win_w = int(config.SCREEN_WIDTH * args.scale)
    win_h = int(config.SCREEN_HEIGHT * args.scale)
    cv2.resizeWindow("ClashBot Live Detection", win_w, win_h)
    bridge_y_frac = config.ARENA_BRIDGE_Y / config.SCREEN_HEIGHT

    # ... rest of the loop stays the same ...
```

---

## Verification Criteria
- [ ] Running `python data/live_detection.py` without `--scale` auto-sizes the window to fit the screen
- [ ] On a 1080p monitor (1920×1080), scale should be ~0.41 → window ~443×984
- [ ] On a 1440p monitor (2560×1440), scale should be ~0.56 → window ~605×1340
- [ ] Running `python data/live_detection.py --scale 0.7` still works as manual override
- [ ] The window can still be manually resized by dragging (WINDOW_NORMAL)
- [ ] The detection boxes and labels are readable at the auto-calculated size

## Notes
- This is a **low-effort, low-risk** change — it only affects the display, not detection or game logic
- The user can always override with `--scale X` if they prefer a specific size
- The `draw_frame()` function doesn't need any changes — it already respects the `scale` parameter
