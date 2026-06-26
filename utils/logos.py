import os
from utils.vars import LOGO_DIR
from PIL import Image

logo_cache = {}

def load_logo(league, abbr):
    key = f"{league}_{abbr}"
    if key in logo_cache:
        return logo_cache[key]

    path = os.path.join(LOGO_DIR, f"{key}.png")
    if not os.path.exists(path):
        print(f"Logo not found: {path}")
        logo_cache[key] = None
        return None

    try:
        # FIX: convert to RGB here so draw_logo always gets 3-channel pixels
        img = Image.open(path).convert("RGB")
        logo_cache[key] = img
        return img
    except Exception as e:
        print(f"Error loading logo {key}: {e}")
        logo_cache[key] = None
        return None

def draw_logo(canvas, img, x, y):
    if img is None:
        return
    for px in range(img.width):
        for py in range(img.height):
            # FIX: unpack as RGB (load_logo guarantees RGB now)
            r, g, b = img.getpixel((px, py))
            canvas.SetPixel(x + px, y + py, b, r, g)  # bgr panels