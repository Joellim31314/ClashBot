"""
Coordinate Debug & Calibration Tool for ClashBot.

Captures a live screenshot from the emulator and tests ALL configured
coordinates against it. Produces a text report and an annotated overlay image.

Works on ANY screen (menu, battle, chest, trophy road, game over).

Usage:
    python debug_coords.py
"""
import sys
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config
from bot.screen import ScreenCapture

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# --- Color helpers ---

def rgb_str(pixel: tuple) -> str:
    return f"RGB({pixel[0]}, {pixel[1]}, {pixel[2]})"


def pixel_in_range(pixel: tuple, lo: tuple, hi: tuple) -> bool:
    return all(l <= v <= h for v, l, h in zip(pixel, lo, hi))


def brightness(pixel: tuple) -> int:
    return pixel[0] + pixel[1] + pixel[2]


# --- Coordinate tests ---

def test_card_slots(pixels: np.ndarray) -> list[dict]:
    """Test each card slot coordinate. Cards should NOT be dark background."""
    results = []
    dark_threshold = 120  # sum of RGB; below this is likely empty/dark bg
    for i, x in enumerate(config.CARD_SLOT_X):
        y = config.CARD_SLOT_Y
        if y >= pixels.shape[0] or x >= pixels.shape[1]:
            results.append({"name": f"Card Slot {i+1}", "x": x, "y": y,
                            "status": "FAIL", "reason": "Out of bounds"})
            continue
        pixel = tuple(pixels[y, x])
        b = brightness(pixel)
        passed = b > dark_threshold
        results.append({
            "name": f"Card Slot {i+1}", "x": x, "y": y,
            "pixel": pixel, "brightness": b,
            "status": "PASS" if passed else "FAIL",
            "reason": f"{rgb_str(pixel)} bright={b}" + ("" if passed else " (too dark — likely NOT on a card)")
        })
    # Next card
    x, y = config.NEXT_CARD_X, config.NEXT_CARD_Y
    if y < pixels.shape[0] and x < pixels.shape[1]:
        pixel = tuple(pixels[y, x])
        b = brightness(pixel)
        results.append({
            "name": "Next Card (5th)", "x": x, "y": y,
            "pixel": pixel, "brightness": b,
            "status": "INFO",
            "reason": f"{rgb_str(pixel)} bright={b}"
        })
    return results


def test_elixir_bar(pixels: np.ndarray) -> list[dict]:
    """Test elixir bar sampling points."""
    results = []
    y = config.ELIXIR_BAR_Y
    x_start = config.ELIXIR_BAR_X_START
    x_end = config.ELIXIR_BAR_X_END
    pip_width = (x_end - x_start) / config.ELIXIR_PIP_COUNT

    filled_count = 0
    for i in range(config.ELIXIR_PIP_COUNT):
        x = int(x_start + pip_width * i + pip_width / 2)
        if y >= pixels.shape[0] or x >= pixels.shape[1]:
            continue
        pixel = tuple(pixels[y, x])
        is_filled = pixel_in_range(pixel, config.ELIXIR_FILLED_COLOR_MIN, config.ELIXIR_FILLED_COLOR_MAX)
        if is_filled:
            filled_count += 1
        results.append({
            "name": f"Elixir Pip {i+1}", "x": x, "y": y,
            "pixel": pixel,
            "status": "FILLED" if is_filled else "EMPTY",
            "reason": rgb_str(pixel)
        })

    # Summary
    results.insert(0, {
        "name": "Elixir Bar Summary", "x": None, "y": y,
        "status": "INFO",
        "reason": f"Detected {filled_count}/10 elixir filled. Y={y}, X range [{x_start}-{x_end}]"
    })
    return results


def test_state_indicators(pixels: np.ndarray) -> list[dict]:
    """Test ALL state indicator pixels and report which ones match."""
    indicators = [
        ("Battle Indicator",     config.BATTLE_INDICATOR_POS,
         config.BATTLE_INDICATOR_COLOR_MIN,    config.BATTLE_INDICATOR_COLOR_MAX),
        ("Trophy Road Indicator", config.TROPHY_ROAD_INDICATOR_POS,
         config.TROPHY_ROAD_INDICATOR_COLOR_MIN, config.TROPHY_ROAD_INDICATOR_COLOR_MAX),
        ("Game Over Indicator",  config.GAME_OVER_INDICATOR_POS,
         config.GAME_OVER_INDICATOR_COLOR_MIN,  config.GAME_OVER_INDICATOR_COLOR_MAX),
        ("Menu Indicator",       config.MENU_INDICATOR_POS,
         config.MENU_INDICATOR_COLOR_MIN,        config.MENU_INDICATOR_COLOR_MAX),
    ]
    results = []
    matched_states = []
    for name, pos, lo, hi in indicators:
        x, y = pos
        if y >= pixels.shape[0] or x >= pixels.shape[1]:
            results.append({"name": name, "x": x, "y": y,
                            "status": "FAIL", "reason": "Out of bounds"})
            continue
        pixel = tuple(pixels[y, x])
        matched = pixel_in_range(pixel, lo, hi)
        if matched:
            matched_states.append(name.replace(" Indicator", ""))
        results.append({
            "name": name, "x": x, "y": y,
            "pixel": pixel,
            "status": "MATCH" if matched else "NO",
            "reason": f"{rgb_str(pixel)} — {'MATCHES range' if matched else 'does not match'}"
                       f"  (range {lo} - {hi})"
        })
    # Summary line at the top
    if matched_states:
        summary = f"Detected state(s): {', '.join(matched_states)}"
    else:
        summary = "No state indicators matched — state would be UNKNOWN"
    results.insert(0, {
        "name": "Detection Summary", "x": None, "y": None,
        "status": "INFO", "reason": summary
    })
    return results


def test_bridges(pixels: np.ndarray) -> list[dict]:
    """Test bridge positions — should be on arena (greenish or grayish ground)."""
    results = []
    for name, pos in [("Left Bridge", config.LEFT_BRIDGE), ("Right Bridge", config.RIGHT_BRIDGE)]:
        x, y = pos
        if y >= pixels.shape[0] or x >= pixels.shape[1]:
            results.append({"name": name, "x": x, "y": y, "status": "FAIL", "reason": "Out of bounds"})
            continue
        pixel = tuple(pixels[y, x])
        results.append({
            "name": name, "x": x, "y": y, "pixel": pixel,
            "status": "INFO",
            "reason": f"{rgb_str(pixel)} — visually verify on overlay"
        })
    return results


def test_towers(pixels: np.ndarray) -> list[dict]:
    """Test tower positions."""
    results = []
    towers = [
        ("Enemy King Tower", config.ENEMY_KING_TOWER),
        ("Enemy Left Princess", config.ENEMY_LEFT_PRINCESS),
        ("Enemy Right Princess", config.ENEMY_RIGHT_PRINCESS),
        ("Friendly King Tower", config.FRIENDLY_KING_TOWER),
        ("Friendly Left Princess", config.FRIENDLY_LEFT_PRINCESS),
        ("Friendly Right Princess", config.FRIENDLY_RIGHT_PRINCESS),
    ]
    for name, pos in towers:
        x, y = pos
        if y >= pixels.shape[0] or x >= pixels.shape[1]:
            results.append({"name": name, "x": x, "y": y, "status": "FAIL", "reason": "Out of bounds"})
            continue
        pixel = tuple(pixels[y, x])
        results.append({
            "name": name, "x": x, "y": y, "pixel": pixel,
            "status": "INFO",
            "reason": f"{rgb_str(pixel)} — visually verify on overlay"
        })
    return results


def test_buttons(pixels: np.ndarray) -> list[dict]:
    """Test UI button positions (menu/post-game/chest/trophy screens)."""
    results = []
    buttons = [
        ("Battle Button", config.BATTLE_BUTTON),
        ("OK Button", config.OK_BUTTON),
        ("Menu Return Button", config.MENU_RETURN_BUTTON),
        ("Trophy Road OK Button", config.TROPHY_ROAD_OK_BUTTON),
        ("Chest Tap Position", config.CHEST_TAP_POS),
    ]
    for name, pos in buttons:
        x, y = pos
        if y >= pixels.shape[0] or x >= pixels.shape[1]:
            results.append({"name": name, "x": x, "y": y, "status": "SKIP", "reason": "Out of bounds"})
            continue
        pixel = tuple(pixels[y, x])
        results.append({
            "name": name, "x": x, "y": y, "pixel": pixel,
            "status": "INFO",
            "reason": f"{rgb_str(pixel)}"
        })
    return results


# --- Annotated overlay ---

COLORS = {
    "Card Slots": (255, 255, 0),      # Yellow
    "Elixir": (200, 0, 255),           # Purple
    "State Indicators": (0, 200, 255), # Cyan
    "Bridges": (0, 255, 0),            # Green
    "Towers": (255, 100, 0),           # Orange
    "Buttons": (255, 255, 255),        # White
}


def draw_crosshair(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple, size: int = 12, label: str = ""):
    """Draw a crosshair with optional label."""
    draw.line([(x - size, y), (x + size, y)], fill=color, width=2)
    draw.line([(x, y - size), (x, y + size)], fill=color, width=2)
    # Small box around center
    draw.rectangle([(x - 2, y - 2), (x + 2, y + 2)], outline=color, width=1)
    if label:
        draw.text((x + size + 3, y - 6), label, fill=color)


def create_overlay(image: Image.Image) -> Image.Image:
    """Create annotated overlay with all coordinate groups."""
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)

    # Card slots
    color = COLORS["Card Slots"]
    for i, x in enumerate(config.CARD_SLOT_X):
        draw_crosshair(draw, x, config.CARD_SLOT_Y, color, label=f"Card{i+1}")
    draw_crosshair(draw, config.NEXT_CARD_X, config.NEXT_CARD_Y, color, label="Next")

    # Elixir pips
    color = COLORS["Elixir"]
    pip_width = (config.ELIXIR_BAR_X_END - config.ELIXIR_BAR_X_START) / config.ELIXIR_PIP_COUNT
    for i in range(config.ELIXIR_PIP_COUNT):
        x = int(config.ELIXIR_BAR_X_START + pip_width * i + pip_width / 2)
        draw_crosshair(draw, x, config.ELIXIR_BAR_Y, color, size=6, label=str(i+1) if i % 3 == 0 else "")

    # State indicators (all 4)
    si_color = COLORS["State Indicators"]
    state_indicators = [
        ("Battle",     config.BATTLE_INDICATOR_POS),
        ("TrophyRd",   config.TROPHY_ROAD_INDICATOR_POS),
        ("GameOver",   config.GAME_OVER_INDICATOR_POS),
        ("Menu",       config.MENU_INDICATOR_POS),
    ]
    for name, pos in state_indicators:
        draw_crosshair(draw, pos[0], pos[1], si_color, label=name)

    # Bridges
    color = COLORS["Bridges"]
    for name, pos in [("LBridge", config.LEFT_BRIDGE), ("RBridge", config.RIGHT_BRIDGE)]:
        draw_crosshair(draw, pos[0], pos[1], color, label=name)

    # Towers
    color = COLORS["Towers"]
    towers = [
        ("EKing", config.ENEMY_KING_TOWER),
        ("ELPrin", config.ENEMY_LEFT_PRINCESS),
        ("ERPrin", config.ENEMY_RIGHT_PRINCESS),
        ("FKing", config.FRIENDLY_KING_TOWER),
        ("FLPrin", config.FRIENDLY_LEFT_PRINCESS),
        ("FRPrin", config.FRIENDLY_RIGHT_PRINCESS),
    ]
    for name, pos in towers:
        draw_crosshair(draw, pos[0], pos[1], color, label=name)

    # Buttons
    color = COLORS["Buttons"]
    for name, pos in [
        ("Battle", config.BATTLE_BUTTON),
        ("OK", config.OK_BUTTON),
        ("MenuRet", config.MENU_RETURN_BUTTON),
        ("TrOK", config.TROPHY_ROAD_OK_BUTTON),
        ("ChestTap", config.CHEST_TAP_POS),
    ]:
        draw_crosshair(draw, pos[0], pos[1], color, size=8, label=name)

    # Draw arena boundary box
    draw.rectangle(
        [(config.ARENA_LEFT_X, config.ARENA_TOP_Y), (config.ARENA_RIGHT_X, config.ARENA_BOTTOM_Y)],
        outline=(100, 255, 100), width=1
    )

    # Add legend
    legend_y = 10
    for group, c in COLORS.items():
        draw.rectangle([(5, legend_y), (15, legend_y + 10)], fill=c)
        draw.text((20, legend_y), group, fill=c)
        legend_y += 15

    # Create zoomed card area crop (3x)
    card_crop = image.crop((0, 1050, 720, 1280))
    card_crop_zoomed = card_crop.resize((card_crop.width * 3, card_crop.height * 3), Image.NEAREST)
    # Draw crosshairs on the zoomed crop too
    zoom_draw = ImageDraw.Draw(card_crop_zoomed)
    for i, x in enumerate(config.CARD_SLOT_X):
        zx = (x) * 3
        zy = (config.CARD_SLOT_Y - 1050) * 3
        draw_crosshair(zoom_draw, zx, zy, COLORS["Card Slots"], size=20, label=f"Card{i+1}")
    # Elixir bar on zoomed
    for i in range(config.ELIXIR_PIP_COUNT):
        ex = int(config.ELIXIR_BAR_X_START + pip_width * i + pip_width / 2) * 3
        ey = (config.ELIXIR_BAR_Y - 1050) * 3
        draw_crosshair(zoom_draw, ex, ey, COLORS["Elixir"], size=10)

    card_crop_zoomed.save("debug_card_zoom.png")
    overlay.save("debug_overlay.png")
    return overlay


# --- Report ---

def print_report(all_results: dict[str, list[dict]]):
    """Print a formatted text report."""
    print("\n" + "=" * 60)
    print("  ClashBot Coordinate Debug Report")
    print("=" * 60)

    issues = []
    for group_name, results in all_results.items():
        print(f"\n--- {group_name} ---")
        for r in results:
            status = r["status"]
            marker = {"PASS": "[OK]", "FAIL": "[!!]", "INFO": "[??]", "SKIP": "[--]",
                       "FILLED": "[##]", "EMPTY": "[  ]"}.get(status, "[??]")
            coord = f"({r['x']}, {r['y']})" if r.get('x') is not None else ""
            print(f"  {marker} {r['name']:25s} {coord:15s} {r['reason']}")
            if status == "FAIL":
                issues.append(r)

    print("\n" + "=" * 60)
    if issues:
        print(f"  {len(issues)} ISSUE(S) FOUND:")
        for r in issues:
            print(f"    - {r['name']} at ({r.get('x')}, {r.get('y')}): {r['reason']}")
        print()
        print("  ACTION: Adjust the failing coordinates in config.py,")
        print("  then re-run this script to confirm fixes.")
    else:
        print("  No obvious failures detected.")
        print("  Check [??] items visually in debug_overlay.png")
    print()
    print("  Files saved:")
    print("    debug_overlay.png    — full screenshot with all crosshairs")
    print("    debug_card_zoom.png  — 3x zoom of card area (y=1050-1280)")
    print()
    print("  TIP: Card slots marked [!!] mean the coordinate lands on")
    print("  dark background instead of a card image. Adjust CARD_SLOT_X")
    print("  and CARD_SLOT_Y in config.py to center on the card icons.")
    print("=" * 60 + "\n")


# --- Main ---

def main():
    print("Connecting to emulator...")
    try:
        sc = ScreenCapture()
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    if not sc.is_connected():
        print("No device found. Is LDPlayer running with ADB enabled?")
        sys.exit(1)

    print("Capturing screenshot...")
    image = sc.capture()
    print(f"Screenshot size: {image.size}")

    if image.size != (config.SCREEN_WIDTH, config.SCREEN_HEIGHT):
        print(f"WARNING: Expected {config.SCREEN_WIDTH}x{config.SCREEN_HEIGHT}, "
              f"got {image.size[0]}x{image.size[1]}!")
        print("Coordinates will likely be wrong. Fix emulator resolution first.")

    # Save raw screenshot too
    image.save("debug_raw.png")
    print("Saved raw screenshot to debug_raw.png")

    pixels = np.array(image)

    # Run all tests
    all_results = {
        "State Indicators": test_state_indicators(pixels),
        "Card Slots": test_card_slots(pixels),
        "Elixir Bar": test_elixir_bar(pixels),
        "Bridge Positions": test_bridges(pixels),
        "Tower Positions": test_towers(pixels),
        "UI Buttons": test_buttons(pixels),
    }

    # Print report
    print_report(all_results)

    # Create overlay
    print("Generating overlay images...")
    create_overlay(image)
    print("Done! Check debug_overlay.png and debug_card_zoom.png")


if __name__ == "__main__":
    main()
