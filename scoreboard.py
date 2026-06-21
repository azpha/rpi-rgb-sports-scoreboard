import os
import govee
import pygame
from time import sleep, time
from PIL import Image, ImageDraw, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from dotenv import load_dotenv
from utils.data import LOGO_DIR, ASSET_DIR
from utils.colors import Colors
import modes.score as score_mode

# --- Load environment vars ---
load_dotenv()

# --- Matrix config ---
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 4
options.parallel = 1
options.hardware_mapping = "regular"
options.gpio_slowdown = 5
options.disable_hardware_pulsing = True
options.brightness = 80

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# --- Govee API ---
if os.environ.get('GOVEE_API_KEY'):
    govee_api = govee.GoveeApi(key=os.environ["GOVEE_API_KEY"])

# --- PyGame Audio ---
# FIX: guard pygame init so a missing audio device on headless Pi doesn't segfault
try:
    pygame.mixer.init()
    audio_available = True
except pygame.error as e:
    print(f"Audio init failed: {e}")
    audio_available = False

# --- Goal celebrations ---
def render_goal_frame(text, text_scale, bg_color, text_color):
    big_h = max(8, int(32 * text_scale))
    big_img = Image.new("RGB", (1024, 128), bg_color)
    big_draw = ImageDraw.Draw(big_img)

    try:
        pil_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", big_h
        )
    except:
        pil_font = ImageFont.load_default()

    bbox = big_draw.textbbox((0, 0), text, font=pil_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    tx = (1024 - tw) // 2
    ty = (128 - th) // 2 - bbox[1]
    big_draw.text((tx, ty), text, font=pil_font, fill=text_color)

    scaled = big_img.resize((256, 32), Image.LANCZOS)

    logo_path = os.path.join(LOGO_DIR, "nhl_BUF.png")
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((28, 28), Image.LANCZOS)

            r, g, b, a = logo.split()
            logo_rbg = Image.merge("RGBA", (r, b, g, a))

            pixels = logo_rbg.load()
            for px in range(logo_rbg.width):
                for py in range(logo_rbg.height):
                    rv, gv, bv, av = pixels[px, py]
                    if rv < 30 and gv < 30 and bv < 30:
                        pixels[px, py] = (rv, gv, bv, 0)

            bg_left = Image.new("RGBA", (28, 28), bg_color + (255,))
            bg_left.paste(logo_rbg, mask=logo_rbg.split()[3])
            scaled.paste(bg_left.convert("RGB"), (2, 2))

            bg_right = Image.new("RGBA", (28, 28), bg_color + (255,))
            bg_right.paste(logo_rbg, mask=logo_rbg.split()[3])
            scaled.paste(bg_right.convert("RGB"), (226, 2))

        except Exception as e:
            print(f"Logo paste error: {e}")

    return scaled

def play_goal_celebration(text, color1, color2):
    global canvas

    # Phase 1: zoom in from tiny to full, alternating bg color
    zoom_steps = [0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95, 1.1, 1.0]
    for _ in range(5):
        for i, scale in enumerate(zoom_steps):
            bg = color1 if i % 2 == 0 else color2
            fg = color2 if i % 2 == 0 else color1
            frame = render_goal_frame(text, scale, bg, fg)
            canvas.Clear()
            draw_pil_image(canvas, frame)
            canvas = matrix.SwapOnVSync(canvas)
            sleep(0.05)

        # Phase 2: rapid flashing at full size
        for i in range(10):
            bg = color1 if i % 2 == 0 else color2
            fg = color2 if i % 2 == 0 else color1
            frame = render_goal_frame(text, 1.0, bg, fg)
            canvas.Clear()
            draw_pil_image(canvas, frame)
            canvas = matrix.SwapOnVSync(canvas)
            sleep(0.12)

        # Phase 3: zoom back out and fade to white flash
        zoom_out = [1.0, 1.1, 1.2, 1.3, 1.4]
        for i, scale in enumerate(zoom_out):
            bg = color2 if i % 2 == 0 else color1
            fg = color1 if i % 2 == 0 else color2
            frame = render_goal_frame(text, scale, bg, fg)
            canvas.Clear()
            draw_pil_image(canvas, frame)
            canvas = matrix.SwapOnVSync(canvas)
            sleep(0.08)

        # Phase 4: white flash to end
        for _ in range(3):
            canvas.Clear()
            frame = render_goal_frame(
                text, 1.0, Colors.SABRES_GOLD.value, Colors.SABRES_BLUE.value
            )
            draw_pil_image(canvas, frame)
            canvas = matrix.SwapOnVSync(canvas)
            sleep(0.1)

    # FIX: don't reassign canvas on .Clear() — it returns None in some bindings
    canvas.Clear()
    canvas = matrix.SwapOnVSync(canvas)

    # stop music if playing
    if audio_available:
        pygame.mixer.music.stop()

    sleep(0.5)

def play_audio(filename):
    if not audio_available:
        return
    pygame.mixer.music.load(os.path.join(ASSET_DIR, filename))
    pygame.mixer.music.play()

# --- Utilities ---
def draw_pil_image(canvas, img):
    # FIX: ensure RGB (no alpha channel) to avoid 4-tuple unpack crash
    img = img.convert("RGB")
    for x in range(img.width):
        for y in range(img.height):
            # FIX: bounds check so we never call SetPixel out of matrix range
            if x >= 256 or y >= 32:
                continue
            r, g, b = img.getpixel((x, y))
            canvas.SetPixel(x, y, b, g, r)  # bgr panels

# --- Main loop ---
def run():
    global canvas

    while True:
        canvas_ref = score_mode.draw_frame(canvas)
        canvas = matrix.SwapOnVSync(canvas_ref)

if __name__ == "__main__":
    run()