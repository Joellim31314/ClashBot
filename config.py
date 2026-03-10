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
CARD_SLOT_X = [185, 310, 440, 565]
# Next card (5th card, partially visible)
NEXT_CARD_X = 85
NEXT_CARD_Y = 1210

# --- Arena Play Zones ---
# Where cards can be placed (your side of the arena)
ARENA_LEFT_X = 80
ARENA_RIGHT_X = 640
ARENA_TOP_Y = 300      # Enemy side (top)
ARENA_BRIDGE_Y = 530   # Bridge line
ARENA_MID_Y = 700      # Center of your side
ARENA_BOTTOM_Y = 1000  # Near your towers

# Bridge positions (common placement spots)
LEFT_BRIDGE = (180, 530)
RIGHT_BRIDGE = (540, 530)

# --- Tower Positions ---
ENEMY_KING_TOWER = (360, 150)
ENEMY_LEFT_PRINCESS = (180, 250)
ENEMY_RIGHT_PRINCESS = (540, 250)
FRIENDLY_KING_TOWER = (360, 1050)
FRIENDLY_LEFT_PRINCESS = (180, 920)
FRIENDLY_RIGHT_PRINCESS = (540, 920)

# --- Elixir Bar ---
# The elixir bar is at the bottom of the screen
# Each elixir pip lights up from left to right
ELIXIR_BAR_Y = 1245
ELIXIR_BAR_X_START = 100
ELIXIR_BAR_X_END = 620
ELIXIR_PIP_COUNT = 10
# Color of a filled elixir pip (purple/pink)
ELIXIR_FILLED_COLOR_MIN = (150, 0, 150)  # RGB lower bound
ELIXIR_FILLED_COLOR_MAX = (255, 100, 255)  # RGB upper bound

# --- UI Buttons ---
BATTLE_BUTTON = (360, 950)       # Main menu "Battle" button
OK_BUTTON = (360, 1050)          # Post-game OK/Continue button
MENU_RETURN_BUTTON = (360, 1200) # Return to menu after game

# --- Game State Detection ---
# Pixel sample points and expected colors for detecting screen state
# These are (x, y, expected_color_range) tuples
# The battle screen has the arena visible
BATTLE_INDICATOR_POS = (360, 50)  # Top center — timer area during battle
BATTLE_INDICATOR_COLOR_MIN = (50, 50, 100)
BATTLE_INDICATOR_COLOR_MAX = (150, 150, 255)

# Menu screen has the Clash Royale logo area
MENU_INDICATOR_POS = (360, 200)   # Center area with menu elements

# --- Timing ---
CAPTURE_INTERVAL = 0.5     # Seconds between screen captures in main loop
ACTION_DELAY_MIN = 0.05    # Minimum delay between actions (seconds)
ACTION_DELAY_MAX = 0.20    # Maximum delay between actions (seconds)
CARD_SELECTION_DELAY_MIN = 0.25  # Delay after selecting a card before placing it
CARD_SELECTION_DELAY_MAX = 0.40
POST_GAME_WAIT = 3.0       # Seconds to wait after game ends
ELIXIR_WAIT_THRESHOLD = 7  # Minimum elixir before playing a card (Phase 1)

# --- Logging ---
LOG_LEVEL = "INFO"
LOG_FILE = "clashbot.log"
