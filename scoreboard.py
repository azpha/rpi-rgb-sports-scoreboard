import requests
import os
import govee
import pygame
from enum import Enum
from time import sleep, time
from PIL import Image, ImageDraw, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from dotenv import load_dotenv

# --- Load environment vars ---
load_dotenv()

# --- Default vars ---
ASSET_DIR = "./assets"
LOGO_DIR = os.path.join(ASSET_DIR, "logos")

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

# --- Font initialization ---
font = graphics.Font()
font_small = graphics.Font()
font_big = graphics.Font()
font.LoadFont(os.path.join(ASSET_DIR, "fonts/7x13.bdf"))
font_small.LoadFont(os.path.join(ASSET_DIR, "fonts/5x7.bdf"))

# try to load a big font for GOAL!, fall back to regular if not available
try:
    font_big.LoadFont(os.path.join(ASSET_DIR, "fonts/9x18.bdf"))
except:
    font_big = font

# --- Logo cache ---
logo_cache = {}


# --- Pre-built colors ---
class Colors(Enum):
    WHITE = (255, 255, 255)
    YELLOW = (255, 200, 0)
    RED = (255, 50, 50)
    SABRES_BLUE = (0, 135, 48)
    SABRES_GOLD = (252, 20, 210)


# --- Govee API ---
govee_api = govee.GoveeApi(key=os.environ["GOVEE_API_KEY"])

# --- PyGame Audio ---
pygame.mixer.init()


# --- Goal celebrations ---
def render_goal_frame(text, text_scale, bg_color, text_color):
    big_h = max(8, int(32 * text_scale))
    big_img = Image.new("RGB", (1024, 128), bg_color)
    big_draw = ImageDraw.Draw(big_img)

    # rpi specific, fall back to default font if not existing
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

    # paste sabres logo on left and right
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

    # clear board
    canvas = canvas.Clear()
    canvas = matrix.SwapOnVSync(canvas)

    # stop music if playing
    pygame.mixer.music.stop()

    # Hold for a moment then return to scoreboard
    sleep(0.5)


def play_audio(filename):
    pygame.mixer.music.load(os.path.join(ASSET_DIR, filename))
    pygame.mixer.music.play()


# --- Utilities ---
def draw_pil_image(canvas, img):
    for x in range(img.width):
        for y in range(img.height):
            r, g, b = img.getpixel((x, y))
            canvas.SetPixel(x, y, b, g, r)  # bgr panels


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
            canvas.SetPixel(x + px, y + py, r, g, b)  # bgr panels


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
            games.append(
                {
                    "league": league,
                    "away": away["team"]["abbreviation"].upper(),
                    "away_score": away["score"],
                    "home": home["team"]["abbreviation"].upper(),
                    "home_score": home["score"],
                    "status": status,
                    "id": event["id"],
                }
            )
        return games
    except Exception as e:
        print(f"Fetch error ({league}): {e}")
        return []


def get_all_scores():
    games = []
    games += get_scores("hockey", "nhl")
    games += get_scores("football", "nfl")
    games += get_scores("basketball", "nba")
    games += get_scores("baseball", "mlb")
    return games


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

        graphics.DrawText(
            canvas,
            font_small,
            offset + 18,
            11,
            graphics.Color(255, 255, 255),
            game["away"],
        )
        graphics.DrawText(
            canvas,
            font_small,
            offset + 18,
            27,
            graphics.Color(255, 255, 255),
            game["home"],
        )

        graphics.DrawText(
            canvas,
            font,
            offset + 40,
            13,
            graphics.Color(255, 255, 255),
            str(game["away_score"]),
        )
        graphics.DrawText(
            canvas,
            font,
            offset + 40,
            29,
            graphics.Color(255, 255, 255),
            str(game["home_score"]),
        )

        if i < 3:
            for row in range(32):
                canvas.SetPixel(offset + 63, row, 40, 40, 40)

def draw_single_game(canvas, game):
    league = game["league"]
    home_logo = load_logo(league, game["home"])
    away_logo = load_logo(league, game["away"])

    draw_logo(canvas, away_logo, 0, 0)
    draw_logo(canvas, home_logo, 0, 16)

    graphics.DrawText(
        canvas,
        font_small,
        18,
        11,
        graphics.Color(255, 255, 255),
        game["away"],
    )
    graphics.DrawText(
        canvas,
        font_small,
        18,
        27,
        graphics.Color(255, 255, 255),
        game["home"],
    )

    graphics.DrawText(
        canvas,
        font,
        40,
        13,
        graphics.Color(255, 255, 255),
        str(game["away_score"]),
    )
    graphics.DrawText(
        canvas,
        font,
        40,
        29,
        graphics.Color(255, 255, 255),
        str(game["home_score"]),
    )
    graphics.DrawText(
        canvas,
        font,
        55,
        23,
        graphics.Color(255,255,255),
        str(game["status"])
    )


# --- Main loop ---
def run():
    global canvas
    preferred_game_on = False
    games = []
    prev_scores = {}
    last_fetch = 0
    current_page = 0
    page_display_time = 8
    last_switch = time()

    current_games = get_all_scores()
    preferred_team = [
        "BUF",
        "TOR",
        "TB"
    ]
    preferred_game = []
    for game in current_games:
        print(game)
        if game['home'] in preferred_team or game['away'] in preferred_team:
            if game['status'] != 'Final':
                preferred_game_on = True
                preferred_game.append(game)

    if preferred_game_on:
        while True:
            draw_single_game(canvas, preferred_game[0])
            canvas = matrix.SwapOnVSync(canvas)
            sleep(0.03)
    else:
        while True:
            now = time()

            if now - last_fetch > 30:
                new_games = get_all_scores()

                # update prev_scores
                for game in new_games:
                    gid = game["id"]
                    try:
                        prev_scores[gid] = (
                            int(game["away_score"]),
                            int(game["home_score"]),
                        )
                    except ValueError:
                        pass

                games = new_games
                last_fetch = now
                if not games:
                    current_page = 0

            if games and now - last_switch > page_display_time:
                current_page = (current_page + 4) % max(len(games), 1)
                last_switch = now

            canvas.Clear()

            if games:
                draw_all_games(canvas, games, current_page)
            else:
                graphics.DrawText(
                    canvas, font, 10, 22, graphics.Color(Colors.RED), "No games today"
                )

            canvas = matrix.SwapOnVSync(canvas)
            sleep(0.03)


if __name__ == "__main__":
    run()
