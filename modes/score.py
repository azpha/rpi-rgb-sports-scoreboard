import requests
import utils.logos as logos
from rgbmatrix import graphics
from utils.colors import Colors
from utils.fonts import font, font_small
from time import time

games = []
last_fetch = 0
current_page = 0
page_display_time = 8
last_switch = time()
show_preferred = True

current_preferred_game = 0
preferred_games = []
preferred_teams = [
    ("BUF", "nfl"),
    ("BUF", "nhl"),
    ("TOR", "mlb"),
    ("LAL", "nba"),
]

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
    print('fetching game scores from espn')
    games = []
    games += get_scores("hockey", "nhl")
    games += get_scores("football", "nfl")
    games += get_scores("basketball", "nba")
    games += get_scores("baseball", "mlb")
    return games

# --- Game drawing ---
def draw_all_games(canvas, games, start_index):
    for i in range(4):
        game_index = (start_index + i) % len(games)
        game = games[game_index]
        offset = i * 64

        league = game["league"]
        away_logo = logos.load_logo(league, game["away"])
        home_logo = logos.load_logo(league, game["home"])

        logos.draw_logo(canvas, away_logo, offset + 0, 0)
        logos.draw_logo(canvas, home_logo, offset + 0, 16)

        graphics.DrawText(
            canvas,
            font_small,
            offset + 18,
            11,
            graphics.Color(*Colors.RED.value),
            game["away"],
        )
        graphics.DrawText(
            canvas,
            font_small,
            offset + 18,
            27,
            graphics.Color(*Colors.WHITE.value),
            game["home"],
        )

        graphics.DrawText(
            canvas,
            font,
            offset + 40,
            13,
            graphics.Color(*Colors.WHITE.value),
            str(game["away_score"]),
        )
        graphics.DrawText(
            canvas,
            font,
            offset + 40,
            29,
            graphics.Color(*Colors.WHITE.value),
            str(game["home_score"]),
        )

        if i < 3:
            for row in range(32):
                canvas.SetPixel(offset + 63, row, 40, 40, 40)

def draw_single_game(canvas, game):
    league = game["league"]
    home_logo = logos.load_logo(league, game["home"])
    away_logo = logos.load_logo(league, game["away"])

    logos.draw_logo(canvas, away_logo, 0, 0)
    logos.draw_logo(canvas, home_logo, 0, 16)

    graphics.DrawText(
        canvas,
        font_small,
        18,
        11,
        graphics.Color(*Colors.WHITE.value),
        game["away"],
    )
    graphics.DrawText(
        canvas,
        font_small,
        18,
        27,
        graphics.Color(*Colors.WHITE.value),
        game["home"],
    )

    graphics.DrawText(
        canvas,
        font,
        40,
        13,
        graphics.Color(*Colors.WHITE.value),
        str(game["away_score"]),
    )
    graphics.DrawText(
        canvas,
        font,
        40,
        29,
        graphics.Color(*Colors.WHITE.value),
        str(game["home_score"]),
    )
    graphics.DrawText(
        canvas,
        font,
        55,
        22,
        graphics.Color(*Colors.WHITE.value),
        str(game["status"])
    )

def draw_frame(canvas):
  now = time()

  if now - last_fetch > 30 or len(games) <= 0:
      games = get_all_scores()
      last_fetch = now

  if games:
      canvas.Clear()

      # clear finished preferred games
      if len(preferred_games) > 0:
          for preferred_game in preferred_games[:]:
              shown_game = [g for g in games if preferred_game == g['id']]
              if len(shown_game) <= 0 or "Final" in shown_game[0]['status']:
                  preferred_games.remove(preferred_game)

      # collect new preferred games
      for game in games:
          if (game['away'], game['league']) in preferred_teams or (game['home'], game['league']) in preferred_teams:
              if 'Final' not in game['status'] and game['id'] not in preferred_games:
                  preferred_games.append(game['id'])

      print(preferred_games)

      if now - last_switch > page_display_time:
          last_switch = now

          if show_preferred and len(preferred_games) > 0:
              single_preferred_game = next(
                  (g for g in games if g['id'] == preferred_games[current_preferred_game]), None
              )
              if single_preferred_game:
                  print(f'Showing preferred game {single_preferred_game["home"]} vs {single_preferred_game["away"]}')
                  draw_single_game(canvas, single_preferred_game)

              current_preferred_game += 1
              if current_preferred_game >= len(preferred_games):
                  show_preferred = False
                  current_preferred_game = 0
                  current_page = 0
          else:
              print(f'Showing all games page {current_page} / {len(games)}')
              draw_all_games(canvas, games, current_page)
              current_page += 4
              if current_page >= len(games):
                  current_page = 0
                  if len(preferred_games) > 0:
                      show_preferred = True
  else:
      canvas.Clear()
      print('No games available')
      graphics.DrawText(canvas, font, 10, 22, graphics.Color(*Colors.RED.value), "No games today")

  # canvas = matrix.SwapOnVSync(canvas)
  # sleep(10)
  return canvas