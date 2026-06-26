from enum import Enum
from pathlib import Path
from rgbmatrix import graphics
import os

# --- Pre-built colors ---
class Colors(Enum):
    WHITE = (255, 255, 255)
    YELLOW = (255, 200, 0)
    RED = (255, 50, 50)
    SABRES_BLUE = (0, 135, 48)
    SABRES_GOLD = (252, 20, 210)

SCRIPT_DIR = Path(__file__).parent.resolve()
ASSET_DIR = os.path.join(SCRIPT_DIR, "../assets")
LOGO_DIR = os.path.join(ASSET_DIR, "logos")

PANEL_WIDTH = 256
PANEL_HEIGHT = 32
GAME_WIDTH = 128
DIVIDER_COLOR = (40, 40, 40)

font = graphics.Font()
font_small = graphics.Font()
font_big = graphics.Font()
font.LoadFont(os.path.join(ASSET_DIR, "fonts/7x13.bdf"))
font_small.LoadFont(os.path.join(ASSET_DIR, "fonts/5x7.bdf"))
font_big.LoadFont(os.path.join(ASSET_DIR, "fonts/9x18.bdf"))