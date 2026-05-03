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

# A smaller font for status text
font_small = graphics.Font()
font_small.LoadFont("/usr/local/share/5x7.bdf")

white  = graphics.Color(255, 255, 255)
yellow = graphics.Color(255, 200, 0)
red    = graphics.Color(255, 50, 50)
grey   = graphics.Color(180, 180, 180)

LOGO_DIR = "/home/alex/logos"

# --- Logo cache ---
logo_cache = {}

def load_logo(league, abbr):
    key = f"{league}_{abbr}"
    if key in logo_cache:
        return logo_cache[key]

    path = os.path.join(LOGO_DIR, f"{key}.png")
    if not os.path.exists(path):
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

# --- Draw a single game in stacked layout ---
# Layout per panel (64px wide, 32px tall):
# Top half (rows 0-15):  [16x16 away logo] [away abbr] [away score]
# Bottom half (rows 16-31): [16x16 home logo] [home abbr] [home score]
# Status text scrolls across the bottom row

def draw_game(canvas, game):
    league = game["league"]

    away_logo = load_logo(league, game["away"])
    home_logo = load_logo(league, game["home"])

    # Draw logos
    draw_logo(canvas, away_logo, 0, 0)   # top left
    draw_logo(canvas, home_logo, 0, 16)  # bottom left

    # Draw team abbreviations
    graphics.DrawText(canvas, font_small, 18, 11, white, game["away"])
    graphics.DrawText(canvas, font_small, 18, 27, white, game["home"])

    # Draw scores
    graphics.DrawText(canvas, font, 40, 13, yellow, str(game["away_score"]))
    graphics.DrawText(canvas, font, 40, 29, yellow, str(game["home_score"]))

    # Draw status in grey at far right if short enough, otherwise truncate
    status = game["status"][:10]
    graphics.DrawText(canvas, font_small, 130, 11, grey, status)

# --- Main loop ---
def run():
    global canvas
    games = []
    last_fetch = 0
    current_game = 0
    game_display_time = 8  # seconds per game
    last_switch = time.time()

    while True:
        now = time.time()

        # Re-fetch every 30 seconds
        if now - last_fetch > 30:
            games = get_all_scores()
            last_fetch = now
            if not games:
                current_game = 0

        # Switch game every N seconds
        if games and now - last_switch > game_display_time:
            current_game = (current_game + 1) % len(games)
            last_switch = now

        canvas.Clear()

        if games:
            current_game = current_game % len(games)
            draw_game(canvas, games[current_game])
        else:
            graphics.DrawText(canvas, font, 10, 22, red, "No games today")

        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.03)

if __name__ == "__main__":
    run()