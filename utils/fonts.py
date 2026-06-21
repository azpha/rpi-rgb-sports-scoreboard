from rgbmatrix import graphics
from utils.data import ASSET_DIR
import os

font = graphics.Font()
font_small = graphics.Font()
font_big = graphics.Font()
font.LoadFont(os.path.join(ASSET_DIR, "fonts/7x13.bdf"))
font_small.LoadFont(os.path.join(ASSET_DIR, "fonts/5x7.bdf"))
font_big.LoadFont(os.path.join(ASSET_DIR, "fonts/9x18.bdf"))