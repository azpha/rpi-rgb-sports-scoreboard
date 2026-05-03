import time
import requests
import os
import govee
from time import sleep
from PIL import Image, ImageDraw, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

# --- Matrix config ---
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 4
options.parallel = 1
options.hardware_mapping = 'regular'
options.gpio_slowdown = 5
options.disable_hardware_pulsing = True
options.brightness = 80

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

font = graphics.Font()
font.LoadFont("/usr/local/share/7x13.bdf")

font_small = graphics.Font()
font_small.LoadFont("/usr/local/share/5x7.bdf")

# try to load a big font for GOAL!, fall back to regular if not available
font_big = graphics.Font()
try:
    font_big.LoadFont("/usr/local/share/9x18.bdf")
except:
    font_big = font

white      = graphics.Color(255, 255, 255)
yellow     = graphics.Color(255, 200, 0)
red        = graphics.Color(255, 50, 50)
grey       = graphics.Color(180, 180, 180)
sabres_blue = graphics.Color(0, 135, 48)
sabres_gold = graphics.Color(252, 20, 210)

LOGO_DIR = "/usr/local/share/logos"
SABRES_ABBR = "BUF"
GOVEE_DEVICE = "3D:22:D7:94:40:46:2F:72"
GOVEE_SKU = "H6168"
GOVEE_AWS = "owABAgT/AGQMACr//+YAADb//8k=,o//QAAIDAwAAAAAAAAAAAAAAAI4=,MwUKdwAAAAAAAAAAAAAAAAAAAEs="
GOVEE_IP = "172.16.0.15"

# --- Logo cache ---
logo_cache = {}

# --- Govee API ---
govee_api = govee.GoveeApi(device_ip=GOVEE_IP)

def render_goal_frame(text, text_scale, bg_color, text_color):
    big_h = max(8, int(32 * text_scale))
    big_img = Image.new("RGB", (1024, 128), bg_color)
    big_draw = ImageDraw.Draw(big_img)

    try:
        pil_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", big_h)
    except:
        pil_font = ImageFont.load_default()

    bbox = big_draw.textbbox((0, 0), text, font=pil_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    tx = (1024 - tw) // 2
    ty = (128 - th) // 2 - bbox[1]
    big_draw.text((tx, ty), text, font=pil_font, fill=text_color)

    scaled = big_img.resize((256, 32), Image.LANCZOS)

    # paste sabres logo on left and right
    # Replace the logo paste section with this
    logo_path = os.path.join(LOGO_DIR, "nhl_BUF.png")
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((28, 28), Image.LANCZOS)

            # swap G and B channels for RBG order
            r, g, b, a = logo.split()
            logo_rbg = Image.merge("RGBA", (r, b, g, a))

            # make near-black pixels transparent
            pixels = logo_rbg.load()
            for px in range(logo_rbg.width):
                for py in range(logo_rbg.height):
                    rv, gv, bv, av = pixels[px, py]
                    if rv < 30 and gv < 30 and bv < 30:
                        pixels[px, py] = (rv, gv, bv, 0)

            # paste with transparency onto bg-colored canvas
            bg_left = Image.new("RGBA", (28, 28), bg_color + (255,))
            bg_left.paste(logo_rbg, mask=logo_rbg.split()[3])
            scaled.paste(bg_left.convert("RGB"), (2, 2))

            bg_right = Image.new("RGBA", (28, 28), bg_color + (255,))
            bg_right.paste(logo_rbg, mask=logo_rbg.split()[3])
            scaled.paste(bg_right.convert("RGB"), (226, 2))

        except Exception as e:
            print(f"Logo paste error: {e}")

    return scaled

def draw_pil_image(canvas, img):
    for x in range(img.width):
        for y in range(img.height):
            r, g, b = img.getpixel((x, y))
            canvas.SetPixel(x, y, b, g, r)  # swap r and g for GRB panels

def play_goal_celebration():
    global canvas

    BLUE = (0, 135, 48)   # was (0, 48, 135)
    GOLD = (252, 20, 210) # was (252, 210, 20)
    WHITE = (255, 255, 255) # unchanged
    TEXT = "SABRES GOAL!"

    # Phase 1: zoom in from tiny to full, alternating bg color
    zoom_steps = [0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95, 1.1, 1.0]
    for i, scale in enumerate(zoom_steps):
        bg = BLUE if i % 2 == 0 else GOLD
        fg = GOLD if i % 2 == 0 else BLUE
        frame = render_goal_frame(TEXT, scale, bg, fg)
        canvas.Clear()
        draw_pil_image(canvas, frame)
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.05)

    # Phase 2: rapid flashing at full size
    for i in range(10):
        bg = BLUE if i % 2 == 0 else GOLD
        fg = GOLD if i % 2 == 0 else BLUE
        frame = render_goal_frame(TEXT, 1.0, bg, fg)
        canvas.Clear()
        draw_pil_image(canvas, frame)
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.12)

    # Phase 3: zoom back out and fade to white flash
    zoom_out = [1.0, 1.1, 1.2, 1.3, 1.4]
    for i, scale in enumerate(zoom_out):
        bg = GOLD if i % 2 == 0 else BLUE
        fg = BLUE if i % 2 == 0 else GOLD
        frame = render_goal_frame(TEXT, scale, bg, fg)
        canvas.Clear()
        draw_pil_image(canvas, frame)
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.08)

    # Phase 4: white flash to end
    for _ in range(3):
        canvas.Clear()
        frame = render_goal_frame(TEXT, 1.0, WHITE, BLUE)
        draw_pil_image(canvas, frame)
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.1)
        canvas.Clear()
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.08)

    # Hold for a moment then return to scoreboard
    time.sleep(0.5)

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
            r, g, b = img.getpixel((px, py))
            canvas.SetPixel(x + px, y + py, r, b, g)  # RBG order

# --- Fetch scores ---
def get_scores(sport, league):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        games = []
        for event in resp.json().get("events", []):
            comp = event["competitions"][0]
            teams = comp["competitors"]
            home = next(t for t in teams if t["homeAway"] == "home")
            away = next(t for t in teams if t["homeAway"] == "away")
            status = event["status"]["type"]["shortDetail"]
            games.append({
                "league": league,
                "away": away["team"]["abbreviation"].upper(),
                "away_score": away["score"],
                "home": home["team"]["abbreviation"].upper(),
                "home_score": home["score"],
                "status": status,
                "id": event["id"],
            })
        return games
    except Exception as e:
        print(f"Fetch error ({league}): {e}")
        return []

def get_all_scores():
    games = []
    games += get_scores("hockey", "nhl")
    games += get_scores("football", "nfl")
    games += get_scores("basketball", "nba")
    return games

def sabres_scored(games, prev_scores):
    for game in games:
        if game["away"] != SABRES_ABBR and game["home"] != SABRES_ABBR:
            continue
        gid = game["id"]
        try:
            away = int(game["away_score"])
            home = int(game["home_score"])
        except ValueError:
            continue

        if gid not in prev_scores:
            continue

        prev_away, prev_home = prev_scores[gid]
        if game["away"] == SABRES_ABBR and away > prev_away:
            return True
        if game["home"] == SABRES_ABBR and home > prev_home:
            return True
    return False

# --- Goal celebration ---
def fill_background(canvas, color):
    for x in range(256):
        for y in range(32):
            canvas.SetPixel(x, y, *color)

# --- Draw all games across all panels ---
def draw_all_games(canvas, games, start_index):
    for i in range(4):
        game_index = (start_index + i) % len(games)
        game = games[game_index]
        offset = i * 64

        league = game["league"]
        away_logo = load_logo(league, game["away"])
        home_logo = load_logo(league, game["home"])

        draw_logo(canvas, away_logo, offset + 0, 0)
        draw_logo(canvas, home_logo, offset + 0, 16)

        graphics.DrawText(canvas, font_small, offset + 18, 11, white, game["away"])
        graphics.DrawText(canvas, font_small, offset + 18, 27, white, game["home"])

        graphics.DrawText(canvas, font, offset + 40, 13, yellow, str(game["away_score"]))
        graphics.DrawText(canvas, font, offset + 40, 29, yellow, str(game["home_score"]))

        if i < 3:
            for row in range(32):
                canvas.SetPixel(offset + 63, row, 40, 40, 40)

# --- Main loop ---
def run():
    global canvas
    games = []
    prev_scores = {}
    last_fetch = 0
    current_page = 0
    page_display_time = 8
    last_switch = time.time()

    while True:
        govee_api.send_scene(GOVEE_AWS)
        play_goal_celebration()
        sleep(10)
        govee_api.set_to_original_color()

    # while True:
    #     now = time.time()

    #     if now - last_fetch > 30:
    #         new_games = get_all_scores()

    #         # check for sabres goal before updating prev_scores
    #         if prev_scores and sabres_scored(new_games, prev_scores):
    #             play_goal_celebration()

    #         # update prev_scores
    #         for game in new_games:
    #             gid = game["id"]
    #             try:
    #                 prev_scores[gid] = (int(game["away_score"]), int(game["home_score"]))
    #             except ValueError:
    #                 pass

    #         games = new_games
    #         last_fetch = now
    #         if not games:
    #             current_page = 0

    #     if games and now - last_switch > page_display_time:
    #         current_page = (current_page + 4) % max(len(games), 1)
    #         last_switch = now

    #     canvas.Clear()

    #     if games:
    #         draw_all_games(canvas, games, current_page)
    #     else:
    #         graphics.DrawText(canvas, font, 10, 22, red, "No games today")

    #     canvas = matrix.SwapOnVSync(canvas)
    #     time.sleep(0.03)

if __name__ == "__main__":
    run()