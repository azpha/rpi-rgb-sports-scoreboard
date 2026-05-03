import time
import requests
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

white = graphics.Color(255, 255, 255)
red   = graphics.Color(255, 50, 50)

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
                "away": away["team"]["abbreviation"],
                "away_score": away["score"],
                "home": home["team"]["abbreviation"],
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
    # games += get_scores("football", "nfl")
    # games += get_scores("basketball", "nba")
    return games

# --- Format display string ---
def format_game(game):
    return f"{game['away']} {game['away_score']}  {game['home']} {game['home_score']}  {game['status']}"

# --- Main loop ---
def run():
    global canvas
    games = []
    last_fetch = 0
    current_game = 0
    scroll_pos = canvas.width

    while True:
        now = time.time()

        # Re-fetch every 30 seconds
        if now - last_fetch > 30:
            games = get_all_scores()
            last_fetch = now

        canvas.Clear()

        if games:
            current_game = current_game % len(games)
            text = format_game(games[current_game])
            text_width = graphics.DrawText(canvas, font, scroll_pos, 22, white, text)

            scroll_pos -= 2

            if scroll_pos + text_width < 0:
                scroll_pos = canvas.width
                current_game = (current_game + 1) % len(games)
        else:
            graphics.DrawText(canvas, font, 10, 22, red, "No games today")

        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.03)

if __name__ == "__main__":
    run()