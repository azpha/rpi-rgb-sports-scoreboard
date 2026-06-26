import requests
import utils.logos as logos
from PIL import Image, ImageDraw
from rgbmatrix import graphics
from utils.vars import Colors, font, font_small
from time import time

# --- State ---
_games = []
_last_fetch = 0
_preferred_games = []
_preferred_teams = [
    ("BUF", "nfl"),
    ("BUF", "nhl"),
    ("TOR", "mlb"),
    ("LAL", "nba"),
    ("NYY", "mlb")
]

# Carousel scroll state
_scroll_x = 0
_scroll_speed = 1          # pixels per frame
_frames_per_tick = 2       # how many main loop ticks per scroll step (lower = faster)
_tick = 0
_virtual_canvas = None     # PIL Image of the full wide render
_virtual_dirty = True      # rebuild the virtual canvas on next frame

PANEL_WIDTH = 256          # 4 × 64px panels
PANEL_HEIGHT = 32
GAME_WIDTH = 128            # each game slot is one panel wide
DIVIDER_COLOR = (40, 40, 40)

# --- Color helpers ---
def _rbg(color_tuple):
    """Convert an (R, G, B) tuple to a graphics.Color with G and B swapped
    to correct for RBG panel channel ordering on Waveshare P2.5 panels.
    Hardware channel order is (R, B, G) but the API expects (R, G, B),
    so we swap G and B before passing values in."""
    r, g, b = color_tuple
    return graphics.Color(r, b, g)

# --- Fetch ---
def _get_scores(sport, league):
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

def _get_all_scores():
    print("fetching game scores from espn")
    result = []
    result += _get_scores("hockey", "nhl")
    result += _get_scores("football", "nfl")
    result += _get_scores("basketball", "nba")
    result += _get_scores("baseball", "mlb")
    return result

# --- Build ordered game list: preferred first, then rest ---
def _ordered_games():
    preferred_ids = set(_preferred_games)
    preferred = [g for g in _games if g["id"] in preferred_ids]
    return preferred

# --- Render a single game slot into a PIL image at a given x offset ---
def _render_game_to_pil(img, game, x_offset):
    league = game["league"]

    # logos
    away_logo = logos.load_logo(league, game["away"])
    home_logo = logos.load_logo(league, game["home"])
    if away_logo:
        img.paste(away_logo.resize((14, 14)), (x_offset, 0))
    if home_logo:
        img.paste(home_logo.resize((14, 14)), (x_offset, 16))

    # divider on right edge (except last slot handled by wrapping)
    for row in range(PANEL_HEIGHT):
        img.putpixel((x_offset + GAME_WIDTH - 1, row), DIVIDER_COLOR)

# --- Build the full virtual PIL canvas for all ordered games ---
def _build_virtual_canvas():
    ordered = _ordered_games()
    if not ordered:
        return None

    # wide enough for all games, plus one extra copy at the end for seamless wrap
    total_games = len(ordered)
    total_width = GAME_WIDTH * (total_games + 4)  # +4 so wrap tail fills display
    img = Image.new("RGB", (total_width, PANEL_HEIGHT), (0, 0, 0))

    for i, game in enumerate(ordered * 2):  # duplicate for seamless wrap
        if i >= total_games + 4:
            break
        _render_game_to_pil(img, game, i * GAME_WIDTH)

    return img, total_games

# --- Blit a 256-wide slice of the virtual canvas onto the rgbmatrix canvas ---
def _blit_slice(canvas, pil_img, x_offset):
    total_width = pil_img.width
    for x in range(PANEL_WIDTH):
        src_x = (x_offset + x) % total_width
        for y in range(PANEL_HEIGHT):
            r, g, b = pil_img.getpixel((src_x, y))
            canvas.SetPixel(x, y, r, b, g)  # RBG panels: swap G and B

# --- Draw text onto the virtual canvas using PIL (since rgbmatrix fonts need a real canvas) ---
# We use rgbmatrix DrawText on the live canvas offset by -scroll_x for text only,
# and PIL for logos/backgrounds. See draw_frame() for how these combine.

def _draw_text_overlay(canvas, ordered, scroll_x):
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
                              _rbg(Colors.RED.value), game["away"])
            graphics.DrawText(canvas, font_small, x + 18, 27,
                              _rbg(Colors.WHITE.value), game["home"])
            graphics.DrawText(canvas, font, x + 40, 13,
                              _rbg(Colors.WHITE.value), str(game["away_score"]))
            graphics.DrawText(canvas, font, x + 40, 29,
                              _rbg(Colors.WHITE.value), str(game["home_score"]))

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

                graphics.DrawText(canvas, font_small, x + 65, 15,
                                  _rbg(Colors.YELLOW.value), date)
                graphics.DrawText(canvas, font_small, x + 65, 25,
                                  _rbg(Colors.YELLOW.value), time)
                print(game)
            else:
                graphics.DrawText(canvas, font_small, x + 65, 20,
                                  _rbg(Colors.YELLOW.value), game["status"])



# --- Preferred / stale game management ---
def _update_preferred():
    preferred_id_set = set(_preferred_games)

    # remove finished or gone games
    active_ids = {g["id"] for g in _games}
    for gid in list(_preferred_games):
        game = next((g for g in _games if g["id"] == gid), None)
        if game is None or "Final" in game["status"]:
            _preferred_games.remove(gid)

    # add new matching games
    for game in _games:
        if (game["away"], game["league"]) in _preferred_teams or \
           (game["home"], game["league"]) in _preferred_teams:
            _preferred_games.append(game["id"])

# --- Public draw_frame ---
def draw_frame(canvas):
    global _games, _last_fetch, _virtual_canvas, _virtual_dirty, _scroll_x, _tick

    now = time()

    # refresh scores every 30s
    if now - _last_fetch > 30 or not _games:
        _games = _get_all_scores()
        _last_fetch = now
        _update_preferred()
        _virtual_dirty = True

    if not _games:
        canvas.Clear()
        graphics.DrawText(canvas, font, 10, 22,
                          _rbg(Colors.RED.value), "No games today")
        return canvas

    # rebuild virtual canvas if data changed
    if _virtual_dirty or _virtual_canvas is None:
        result = _build_virtual_canvas()
        if result:
            _virtual_canvas, _total_games = result
        _virtual_dirty = False
        _scroll_x = 0

    ordered = _ordered_games()
    total_scroll_width = GAME_WIDTH * len(ordered)

    canvas.Clear()

    # blit the PIL image slice (logos + dividers + backgrounds)
    if _virtual_canvas:
        _blit_slice(canvas, _virtual_canvas, _scroll_x)

    # draw text on top via rgbmatrix (handles fonts correctly)
    _draw_text_overlay(canvas, ordered, _scroll_x)

    # advance scroll every N ticks
    _tick += 1
    if _tick >= _frames_per_tick:
        _tick = 0
        _scroll_x = (_scroll_x + _scroll_speed) % total_scroll_width

    return canvas