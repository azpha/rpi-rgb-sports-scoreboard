import requests
from PIL import Image
from time import time
from rgbmatrix import graphics
from vars import PANEL_HEIGHT, PANEL_WIDTH, GAME_WIDTH, DIVIDER_COLOR, Colors, font, font_small

games = []
last_fetch = 0
preferred_games = []
preferred_teams = []

scroll_x = 0
scroll_speed = 1
frames_per_tick = 2
tick = 0
times_scrolled = 0
virtual_canvas = None
virtual_dirty = True

def get_scores(sport, league):
  url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
  try:
      resp = requests.get(url, timeout=5)
      resp.raise_for_status()
      result = []
      for event in resp.json().get("events", []):
          comp = event["competitions"][0]
          teams = comp["competitors"]
          home = next(t for t in teams if t["homeAway"] == "home")
          away = next(t for t in teams if t["homeAway"] == "away")
          status = event["status"]["type"]["shortDetail"]
          result.append({
              "league": league,
              "venue": comp["venue"]["fullName"],
              "away": away["team"]["abbreviation"].upper(),
              "away_score": away["score"],
              "home": home["team"]["abbreviation"].upper(),
              "home_score": home["score"],
              "status": status,
              "id": event["id"],
          })
      return result
  except Exception as e:
      print(f"Fetch error ({league}): {e}")
      return []

def get_all_scores():
    print("fetching game scores from espn")
    result = []
    result += get_scores("hockey", "nhl")
    result += get_scores("football", "nfl")
    result += get_scores("basketball", "nba")
    result += get_scores("baseball", "mlb")
    return result

def ordered_games():
    preferred_ids = set(preferred_games)
    preferred = [g for g in games if g["id"] in preferred_ids]
    return preferred

def update_preferred():
    for gid in list(preferred_games):
        game = next((g for g in games if g["id"] == gid), None)
        if game is None or "Final" in game["status"]:
            preferred_games.remove(gid)

    # add new matching games
    for game in games:
        if (game["away"], game["league"]) in preferred_teams or \
           (game["home"], game["league"]) in preferred_teams:
            preferred_games.append(game["id"])

def draw_text_overlay(canvas, ordered, scroll_x):
    """Draw all game text onto the rgbmatrix canvas accounting for scroll offset."""
    total_width = GAME_WIDTH * len(ordered)

    for i, game in enumerate(ordered):
        base_x = (i * GAME_WIDTH) - scroll_x

        # draw twice to handle the wrap-around copy
        for wrap in [0, total_width]:
            x = base_x + wrap

            # cull slots fully off screen
            if x + GAME_WIDTH < 0 or x >= PANEL_WIDTH:
                continue

            graphics.DrawText(canvas, font_small, x + 18, 11,
                              Colors.RED.value, game["away"])
            graphics.DrawText(canvas, font_small, x + 18, 27,
                              Colors.WHITE.value, game["home"])
            graphics.DrawText(canvas, font, x + 40, 13,
                              Colors.WHITE.value, str(game["away_score"]))
            graphics.DrawText(canvas, font, x + 40, 29,
                              Colors.WHITE.value, str(game["home_score"]))

            # status line — only on preferred games (they get a wider single-game view)
            # if game["id"] in set(_preferred_games):
            #     graphics.DrawText(canvas, font_small, x + 18, 20,
            #                       _rbg(Colors.YELLOW.value), "\n".join(game["status"].split("-")))

            # if the time is shown it should be split between lines
            # if not, just display the status
            if "AM" in game["status"] or "PM" in game["status"]:
                game_status_split = game["status"].split("-")
                date = game_status_split[0].strip()
                time = game_status_split[1].strip()

                graphics.DrawText(canvas, font_small, x + 60, 10,
                                  Colors.YELLOW.value, date)
                graphics.DrawText(canvas, font_small, x + 60, 20,
                                  Colors.YELLOW.value, time)
                graphics.DrawText(canvas, font_small, x + 60, 30,
                                  Colors.YELLOW.value, game["venue"])
            else:
                graphics.DrawText(canvas, font_small, x + 65, 20,
                                  Colors.YELLOW.value, game["status"])

def render_game(matrix, img, game, x_offset):
    league = game["league"]

    away_logo = matrix.load_logo_to_image(league, game["away"])
    home_logo = matrix.load_logo_to_image(league, game["home"])
    if away_logo:
        img.paste(away_logo.resize((14, 14)), (x_offset, 0))
    if home_logo:
        img.paste(home_logo.resize((14, 14)), (x_offset, 16))

    # divider on right edge (except last slot handled by wrapping)
    for row in range(PANEL_HEIGHT):
        img.putpixel((x_offset + GAME_WIDTH - 1, row), DIVIDER_COLOR)

def build_canvas(matrix):
    ordered = ordered_games()
    if not ordered:
        return None

    total_games = len(ordered)
    total_width = GAME_WIDTH * (total_games + 4)
    img = Image.new("RGB", (total_width, PANEL_HEIGHT), (0,0,0))

    for i, game in enumerate(ordered * 2):
        if i >= total_games + 4:
            break
        render_game(matrix, img, game, i * GAME_WIDTH)

    return img, total_games

def blit_slice(canvas, pil_img, x_offset):
    total_width = pil_img.width
    for x in range(PANEL_WIDTH):
        src_x = (x_offset + x) % total_width
        for y in range(PANEL_HEIGHT):
            r, g, b = pil_img.getpixel((src_x, y))
            canvas.SetPixel(x, y, r, b, g)

def draw_frame(matrix):
    global games, last_fetch, virtual_canvas, virtual_dirty, scroll_x, tick
    global total_games
    now = time()

    if now - last_fetch > 30 or not games:
        games = get_all_scores()
        last_fetch = now
        update_preferred()
        virtual_dirty = True

    # rebuild virtual canvas if data changed
    if virtual_dirty or virtual_canvas is None:
        result = build_canvas(matrix)
        if result:
            virtual_canvas, total_games = result
            virtual_dirty = False
            scroll_x = 0

    ordered = ordered_games()          # after the fetch, not before
    matrix.canvas.Clear()

    if not ordered:
        graphics.DrawText(matrix.canvas, font, 10, 22,
                          Colors.RED.value, "No games today")
        scroll_x = tick = 0
        return matrix.canvas

    total_scroll_width = GAME_WIDTH * len(ordered)

    if virtual_canvas:
        blit_slice(matrix.canvas, virtual_canvas, scroll_x)
    draw_text_overlay(matrix.canvas, ordered, scroll_x)

    tick += 1
    if tick >= frames_per_tick:
        tick = 0
        next_x = scroll_x + scroll_speed
        if next_x >= total_scroll_width:
            scroll_x = 0
            tick = 0
            matrix.next_slide("fantasy")
            return matrix.canvas
        scroll_x = next_x

    return matrix.canvas