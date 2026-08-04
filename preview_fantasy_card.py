import os
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

# --- stub out rgbmatrix so vars.py / modes/fantasy.py import cleanly on a dev machine ---
from PIL import ImageFont

_FONT_PATH_SIZES = {"4x6.bdf": 6, "5x7.bdf": 7, "7x13.bdf": 12, "9x18.bdf": 16}


def _load_pil_font(px_size):
    for candidate in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf"):
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, px_size)
            except Exception:
                pass
    return ImageFont.load_default()


class _FakeFont:
    def __init__(self):
        self.size = 10
        self.pil_font = _load_pil_font(self.size)

    def LoadFont(self, path):
        # real BDF files are named e.g. "5x7.bdf" / "7x13.bdf" / "9x18.bdf" -
        # use that to pick a comparably-sized stand-in TTF for the preview
        self.size = _FONT_PATH_SIZES.get(os.path.basename(path), 10)
        self.pil_font = _load_pil_font(self.size)


def _fake_draw_text(canvas, font, x, y, color, text):
    r, g, b = color
    offset = getattr(font, "size", 10)
    canvas.draw.text((x, y - offset), text, fill=(r, g, b), font=getattr(font, "pil_font", None))
    return len(text) * (offset // 2 + 1)

def _fake_color(r, g, b):
    return (r, g, b)

_graphics_mod = types.ModuleType("rgbmatrix.graphics")
_graphics_mod.Font = _FakeFont
_graphics_mod.DrawText = _fake_draw_text
_graphics_mod.Color = _fake_color

_rgbmatrix_mod = types.ModuleType("rgbmatrix")
_rgbmatrix_mod.graphics = _graphics_mod

sys.modules["rgbmatrix"] = _rgbmatrix_mod
sys.modules["rgbmatrix.graphics"] = _graphics_mod

# --- safe to import project code now ---
from PIL import Image, ImageDraw
import vars
from modes import fantasy

class FakeCanvas:
    def __init__(self, width, height):
        self.img = Image.new("RGB", (width, height), (0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)

    def Clear(self):
        self.draw.rectangle([0, 0, self.img.width, self.img.height], fill=(0, 0, 0))

    def SetPixel(self, x, y, r, g, b):
        if 0 <= x < self.img.width and 0 <= y < self.img.height:
            self.img.putpixel((x, y), (r, g, b))

class FakeMatrix:
    def __init__(self):
        self.canvas = FakeCanvas(vars.PANEL_WIDTH, vars.PANEL_HEIGHT)
        self._logo_cache = {}

    def load_logo(self, league, abbr):
        key = f"{league}_{abbr}"
        if key in self._logo_cache:
            return self._logo_cache[key]
        path = os.path.join(vars.LOGO_DIR, f"{key}.png")
        if not os.path.exists(path):
            self._logo_cache[key] = None
            return None
        img = Image.open(path).convert("RGB")
        self._logo_cache[key] = img
        return img


def render_single_card(player, out_path, scale=6):
    matrix = FakeMatrix()
    fantasy.players["team1"] = [player]

    img, _ = fantasy.build_canvas(matrix, "team1")
    canvas = matrix.canvas
    fantasy.blit_slice(canvas, img, 0)

    card = canvas.img.crop((0, 0, vars.GAME_WIDTH, vars.PANEL_HEIGHT))
    card = card.resize((card.width * scale, card.height * scale), Image.NEAREST)
    card.save(out_path)
    return out_path


healthy_player = {
    "first_name": "Josh",
    "last_name": "Allen",
    "abbr_name": "J. Allen",
    "position": "QB",
    "team": "BUF",
    "injury_status": None,
    "injury_body_part": None,
}

injured_player = {
    "first_name": "Stefon",
    "last_name": "Diggs",
    "abbr_name": "S. Diggs",
    "position": "WR",
    "team": "BUF",
    "injury_status": "Questionable",
    "injury_body_part": "Hamstring",
}

if __name__ == "__main__":
    healthy_path = REPO_ROOT / "preview_healthy.png"
    injured_path = REPO_ROOT / "preview_injured.png"

    render_single_card(healthy_player, healthy_path)
    render_single_card(injured_player, injured_path)
    print(f"Saved: {healthy_path}")
    print(f"Saved: {injured_path}")

    img1 = Image.open(healthy_path)
    img2 = Image.open(injured_path)
    gap = 20
    combined = Image.new(
        "RGB", (img1.width + img2.width + gap, max(img1.height, img2.height)), (30, 30, 30)
    )
    combined.paste(img1, (0, 0))
    combined.paste(img2, (img1.width + gap, 0))
    combined_path = REPO_ROOT / "preview_comparison.png"
    combined.save(combined_path)
    print(f"Saved: {combined_path}")
    # combined.show()
