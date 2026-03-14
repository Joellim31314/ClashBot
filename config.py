"""
All hardcoded coordinates and constants for ClashBot.
Resolution: 1080x2400 (LDPlayer 9, DPI 320).
Coordinate origin: top-left corner (0,0).

IMPORTANT: Every coordinate in this file is calibrated for 1080x2400.
If the emulator resolution changes, ALL values must be recalibrated.

ESTIMATED from 720x1280 by scaling X*1.5, Y*1.875.
Joel: manually verify each value with DEBUG_STATE_PIXELS=True and
debug_coords.py, then remove this notice.
"""

# --- Emulator Connection ---
ADB_HOST = "127.0.0.1"
ADB_PORT = 5037  # ADB server port (not emulator port)
EMULATOR_SERIAL = "emulator-5554"  # LDPlayer default; adjust if needed

# --- Screen Dimensions ---
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 2400

# --- Card Slots (bottom of screen, 4 card hand) ---
# ESTIMATED — verify with a battle screenshot
CARD_SLOT_Y = 2156
CARD_SLOT_X = [293, 525, 735, 968]
# Next card (5th card, partially visible)
NEXT_CARD_X = 123
NEXT_CARD_Y = 2288

# --- Card Template Matching ---
CARD_CROP_WIDTH = 120   # Width of card crop region for template matching
CARD_CROP_HEIGHT = 188  # Height of card crop region
CARD_CROP_Y_OFFSET = -38  # Offset from card slot center to top of crop
CARD_TEMPLATE_DIR = "data/card_templates"
CARD_MATCH_THRESHOLD = 0.80  # Minimum confidence for template match

# --- Arena Play Zones ---
# ESTIMATED — verify with battle screenshot
ARENA_LEFT_X = 87
ARENA_RIGHT_X = 993
ARENA_TOP_Y = 220       # Enemy side (top)
ARENA_BRIDGE_Y = 994    # Bridge line (river)
ARENA_MID_Y = 1313      # Center of your side
ARENA_BOTTOM_Y = 1656   # Near your towers

# Bridge positions (common placement spots)
LEFT_BRIDGE = (243, 1013)
RIGHT_BRIDGE = (838, 1013)

# --- Tower Positions ---
# ESTIMATED — verify with battle screenshot
ENEMY_KING_TOWER = (540, 230)
ENEMY_LEFT_PRINCESS = (245, 469)
ENEMY_RIGHT_PRINCESS = (840, 469)
FRIENDLY_KING_TOWER = (540, 1650)
FRIENDLY_LEFT_PRINCESS = (245, 1438)
FRIENDLY_RIGHT_PRINCESS = (840, 1438)

# --- Elixir Bar ---
# ESTIMATED — verify with battle screenshot
ELIXIR_BAR_Y = 2353
ELIXIR_BAR_X_START = 315
ELIXIR_BAR_X_END = 1050
ELIXIR_PIP_COUNT = 10
# Color of a filled elixir pip (purple/pink)
ELIXIR_FILLED_COLOR_MIN = (150, 0, 150)  # RGB lower bound
ELIXIR_FILLED_COLOR_MAX = (255, 130, 255)  # RGB upper bound

# --- UI Buttons ---
# ESTIMATED — these are on non-battle screens, verify each one
BATTLE_BUTTON = (540, 1781)       # Main menu "Battle" button
OK_BUTTON = (540, 2050)           # Post-game OK/Continue button
MENU_RETURN_BUTTON = (540, 2050)  # Return to menu after game
TROPHY_ROAD_OK_BUTTON = (540, 2325)  # OK button on the trophy road screen
CHEST_TAP_POS = (540, 1200)           # Center screen — tap to open/dismiss chest
CHEST_TAP_COUNT = 10                   # Number of taps to fully dismiss chest popup

# --- Game State Detection ---
# Each state is identified by a unique pixel indicator on screen.
# Detection priority: BATTLE > TROPHY_ROAD > GAME_OVER > MENU > UNKNOWN.
# All color ranges must be calibrated for your emulator — see DEBUG_STATE_PIXELS.

# Set to True to log pixel values at ALL indicator positions every frame.
# Use this to find the correct color ranges for your emulator resolution.
DEBUG_STATE_PIXELS = True

# BATTLE: Elixir bar pip (purple, only visible during a live match)
# ESTIMATED — verify the purple pip color at the new position
BATTLE_INDICATOR_POS = (240, 2363)
BATTLE_INDICATOR_COLOR_MIN = (150, 0, 150)
BATTLE_INDICATOR_COLOR_MAX = (255, 120, 255)

# TROPHY_ROAD: Trophy road progress screen — left side bar background near bottom.
# CALIBRATE: capture a screenshot on the trophy road and sample this pixel.
TROPHY_ROAD_INDICATOR_POS = (195, 2325)
TROPHY_ROAD_INDICATOR_COLOR_MIN = (20, 60, 100)   # Dark blue lower bound
TROPHY_ROAD_INDICATOR_COLOR_MAX = (80, 130, 180)   # Dark blue upper bound

# GAME_OVER: OK/Continue button on the post-game results screen
# CALIBRATE: run with DEBUG_STATE_PIXELS=True, end a match, and note the pixel color.
GAME_OVER_INDICATOR_POS = (540, 2000)
GAME_OVER_INDICATOR_COLOR_MIN = (50, 130, 200)   # Blue-ish button lower bound
GAME_OVER_INDICATOR_COLOR_MAX = (130, 210, 255)   # Blue-ish button upper bound

# MENU: Battle button on the main menu screen
# CALIBRATE: run with DEBUG_STATE_PIXELS=True on the main menu, and note the pixel color.
MENU_INDICATOR_POS = (540, 1781)
MENU_INDICATOR_COLOR_MIN = (200, 150, 0)         # Golden button lower bound
MENU_INDICATOR_COLOR_MAX = (255, 230, 100)         # Golden button upper bound

# --- Timing ---
CAPTURE_INTERVAL = 0.1     # Seconds between screen captures in main loop (10 Hz)
ACTION_DELAY_MIN = 0.05    # Minimum delay between actions (seconds)
ACTION_DELAY_MAX = 0.20    # Maximum delay between actions (seconds)
CARD_SELECTION_DELAY_MIN = 0.25  # Delay after selecting a card before placing it
CARD_SELECTION_DELAY_MAX = 0.40
POST_GAME_WAIT = 3.0       # Seconds to wait after game ends
ELIXIR_WAIT_THRESHOLD = 7  # Minimum elixir before playing a card (Phase 1)

# --- Logging ---
LOG_LEVEL = "INFO"
LOG_FILE = "clashbot.log"

# --- YOLO Detection ---
YOLO_MODEL_PATH = "models/arena_v1/weights/best.pt"  # Override if using KataCR weights
YOLO_CONFIDENCE_THRESHOLD = 0.40
YOLO_IOU_THRESHOLD = 0.45
