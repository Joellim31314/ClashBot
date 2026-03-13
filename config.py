"""
All hardcoded coordinates and constants for ClashBot.
Resolution: 720x1280 (LDPlayer 9).
Coordinate origin: top-left corner (0,0).

IMPORTANT: Every coordinate in this file is calibrated for 720x1280.
If the emulator resolution changes, ALL values must be recalibrated.
"""

# --- Emulator Connection ---
ADB_HOST = "127.0.0.1"
ADB_PORT = 5037  # ADB server port (not emulator port)
EMULATOR_SERIAL = "emulator-5554"  # LDPlayer default; adjust if needed

# --- Screen Dimensions ---
SCREEN_WIDTH = 720
SCREEN_HEIGHT = 1280

# --- Card Slots (bottom of screen, 4 card hand) ---
# Y coordinate for the center of card slots.
# Calibrated from debug_raw.png captured on 2026-03-09; 1050 was above the hand.
CARD_SLOT_Y = 1150
# X coordinates for each of the 4 card slots (left to right)
CARD_SLOT_X = [195, 350, 490, 645]
# Next card (5th card, partially visible)
NEXT_CARD_X = 82
NEXT_CARD_Y = 1220

# --- Card Template Matching ---
CARD_CROP_WIDTH = 80    # Width of card crop region for template matching
CARD_CROP_HEIGHT = 100  # Height of card crop region
CARD_CROP_Y_OFFSET = -20  # Offset from card slot center to top of crop
CARD_TEMPLATE_DIR = "data/card_templates"
CARD_MATCH_THRESHOLD = 0.80  # Minimum confidence for template match

# --- Arena Play Zones ---
# Where cards can be placed (your side of the arena)
ARENA_LEFT_X = 58
ARENA_RIGHT_X = 662
ARENA_TOP_Y = 100      # Enemy side (top)
ARENA_BRIDGE_Y = 530   # Bridge line
ARENA_MID_Y = 700      # Center of your side
ARENA_BOTTOM_Y = 990  # Near your towers

# Bridge positions (common placement spots)
LEFT_BRIDGE = (175, 540)
RIGHT_BRIDGE = (545, 540)

# --- Tower Positions ---
ENEMY_KING_TOWER = (360, 150)
ENEMY_LEFT_PRINCESS = (180, 250)
ENEMY_RIGHT_PRINCESS = (540, 250)
FRIENDLY_KING_TOWER = (360, 880)
FRIENDLY_LEFT_PRINCESS = (180, 820)
FRIENDLY_RIGHT_PRINCESS = (540, 820)

# --- Elixir Bar ---
# The elixir bar is at the bottom of the screen
# Each elixir pip lights up from left to right
ELIXIR_BAR_Y = 1255
ELIXIR_BAR_X_START = 210
ELIXIR_BAR_X_END = 700
ELIXIR_PIP_COUNT = 10
# Color of a filled elixir pip (purple/pink)
ELIXIR_FILLED_COLOR_MIN = (150, 0, 150)  # RGB lower bound
ELIXIR_FILLED_COLOR_MAX = (255, 130, 255)  # RGB upper bound

# --- UI Buttons ---
BATTLE_BUTTON = (360, 950)       # Main menu "Battle" button
OK_BUTTON = (360, 1180)          # Post-game OK/Continue button
MENU_RETURN_BUTTON = (360, 1180) # Return to menu after game
TROPHY_ROAD_OK_BUTTON = (360, 1240)  # OK button on the trophy road screen
CHEST_TAP_POS = (360, 640)           # Center screen — tap to open/dismiss chest
CHEST_TAP_COUNT = 10                 # Number of taps to fully dismiss chest popup

# --- Game State Detection ---
# Each state is identified by a unique pixel indicator on screen.
# Detection priority: BATTLE > TROPHY_ROAD > GAME_OVER > MENU > UNKNOWN.
# All color ranges must be calibrated for your emulator — see DEBUG_STATE_PIXELS.

# Set to True to log pixel values at ALL indicator positions every frame.
# Use this to find the correct color ranges for your emulator resolution.
DEBUG_STATE_PIXELS = True

# BATTLE: Elixir bar pip (purple, only visible during a live match)
BATTLE_INDICATOR_POS = (160, 1260)
BATTLE_INDICATOR_COLOR_MIN = (150, 0, 150)
BATTLE_INDICATOR_COLOR_MAX = (255, 120, 255)

# TROPHY_ROAD: Trophy road progress screen — left side bar background near bottom.
# CALIBRATE: capture a screenshot on the trophy road and sample this pixel.
TROPHY_ROAD_INDICATOR_POS = (130, 1240)        # Left side bottom bar background
TROPHY_ROAD_INDICATOR_COLOR_MIN = (20, 60, 100)   # Dark blue lower bound
TROPHY_ROAD_INDICATOR_COLOR_MAX = (80, 130, 180)   # Dark blue upper bound

# GAME_OVER: OK/Continue button on the post-game results screen
# CALIBRATE: run with DEBUG_STATE_PIXELS=True, end a match, and note the pixel color.
GAME_OVER_INDICATOR_POS = (360, 1180)          # Center of the OK button
GAME_OVER_INDICATOR_COLOR_MIN = (50, 130, 200)   # Blue-ish button lower bound
GAME_OVER_INDICATOR_COLOR_MAX = (130, 210, 255)   # Blue-ish button upper bound

# MENU: Battle button on the main menu screen
# CALIBRATE: run with DEBUG_STATE_PIXELS=True on the main menu, and note the pixel color.
MENU_INDICATOR_POS = (360, 950)                # Center of the Battle button
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
