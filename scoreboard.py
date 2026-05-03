import time
import requests
import os
from PIL import Image
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
sabres_blue = graphics.Color(0, 48, 135)
sabres_gold = graphics.Color(252, 181, 20)

LOGO_DIR = "/home/alex/logos"
SABRES_ABBR = "BUF"

# --- Logo cache ---
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
            canvas.SetPixel(x + px, y + py, r, g, b)

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

def play_goal_celebration():
    global canvas
    colors = [
        (0, 48, 135),    # sabres blue
        (252, 181, 20),  # sabres gold
    ]

    flashes = 6
    for i in range(flashes):
        bg = colors[i % 2]
        text_color = sabres_gold if i % 2 == 0 else sabres_blue

        canvas.Clear()
        # fill background
        for x in range(256):
            for y in range(32):
                canvas.SetPixel(x, y, bg[0], bg[1], bg[2])

        # draw GOAL! centered across full 256px width
        text = "GOAL!"
        # draw it twice across the display for that arena feel
        graphics.DrawText(canvas, font_big, 20, 22, text_color, text)
        graphics.DrawText(canvas, font_big, 140, 22, text_color, text)

        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.3)

    # hold final frame briefly
    time.sleep(1.0)

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
        play_goal_celebration()

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