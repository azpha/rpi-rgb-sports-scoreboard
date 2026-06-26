import requests
from PIL import Image
from rgbmatrix import graphics
import utils.logos as logos
from utils.vars import Colors, font, font_small, PANEL_WIDTH, PANEL_HEIGHT, GAME_WIDTH, DIVIDER_COLOR
from time import time

FETCH_INTERVAL = 60  # seconds between API calls

# Logo layout: 14x14 centered vertically in the 32px panel
LOGO_SIZE = 14
LOGO_Y    = 9   # (32 - 14) // 2 = 9
TEXT_X    = 17  # x offset for text after logo

# Off-enum colors
_COLOR_GREEN = (0, 200, 80)

# --- State ---
_data          = None
_last_fetch    = 0
_cells         = []
_scroll_x      = 0
_scroll_speed  = 1
_frames_per_tick = 2
_tick          = 0
_virtual_canvas = None
_virtual_dirty  = True


# ---------------------------------------------------------------------------
# RBG channel correction for Waveshare P2.5 panels
# Hardware physical order is R-B-G, so swap G and B before passing to API.
# ---------------------------------------------------------------------------
def _rbg(rgb):
    r, g, b = rgb
    return graphics.Color(r, b, g)


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------
def _fetch():
    try:
        resp = requests.get("https://api.alexav.gg/v4/sports/fantasy", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[fantasy] fetch error: {e}")
        return None


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def _player_name(player):
    """Return a short display name (≤9 chars). DEF units use team abbreviation."""
    if player.get("position") == "DEF":
        return player.get("team", "DEF")[:9]
    first = player.get("first_name", "")
    last  = player.get("last_name", "")
    if first and last:
        return f"{first[0]}.{last}"[:9]
    return (last or first)[:9]


def _team_label(name, maxlen=12):
    """Strip parenthetical suffixes and truncate team name."""
    paren = name.find(" (")
    label = name[:paren] if paren > 0 else name
    return label[:maxlen]


def _fmt_pts(pts):
    """Format fantasy points to one decimal place."""
    return f"{float(pts):.1f}"


# ---------------------------------------------------------------------------
# Build the ordered cell list from API data
# Structure: [Team1 Header] [T1 Player ...] [Team2 Header] [T2 Player ...]
# ---------------------------------------------------------------------------
def _build_cells(data):
    cells = []
    t1, t2 = data["team1"], data["team2"]

    for team, opp in [(t1, t2), (t2, t1)]:
        meta      = team["owner"].get("metadata", {})
        team_name = meta.get("team_name", team["owner"]["display_name"])
        winning   = float(team["points"]) >= float(opp["points"])

        # ── Team summary header cell ──────────────────────────────────────
        cells.append({
            "type":       "team_info",
            "owner":      team["owner"]["display_name"],
            "team_name":  team_name,
            "points":     team["points"],
            "opp_points": opp["points"],
            "winning":    winning,
        })

        # ── One cell per starter ─────────────────────────────────────────
        pp = team["players_points"]
        for player in team["starters"]:
            pid    = player["player_id"]
            injury = player.get("injury_status")
            cells.append({
                "type":     "player",
                "nfl_team": player.get("team", ""),
                "name":     _player_name(player),
                "position": player.get("position", ""),
                "points":   pp.get(pid, 0),
                "injury":   injury,
            })

    return cells


# ---------------------------------------------------------------------------
# PIL canvas: logos + dividers (blit-able background layer)
# ---------------------------------------------------------------------------
def _build_virtual_canvas(cells):
    if not cells:
        return None
    n       = len(cells)
    total_w = GAME_WIDTH * (n + 4)   # +4 tail so wrap never shows black
    img     = Image.new("RGB", (total_w, PANEL_HEIGHT), (0, 0, 0))

    for i, cell in enumerate(cells * 2):
        if i >= n + 4:
            break
        _render_pil(img, cell, i * GAME_WIDTH)

    return img, n


def _render_pil(img, cell, x):
    # right-edge divider
    for y in range(PANEL_HEIGHT):
        img.putpixel((x + GAME_WIDTH - 1, y), DIVIDER_COLOR)

    # NFL team logo for player cells
    if cell["type"] == "player" and cell["nfl_team"]:
        logo = logos.load_logo("nfl", cell["nfl_team"])
        if logo:
            img.paste(logo.resize((LOGO_SIZE, LOGO_SIZE)), (x + 1, LOGO_Y))


# ---------------------------------------------------------------------------
# Blit a PANEL_WIDTH-wide slice from the PIL canvas to the matrix
# ---------------------------------------------------------------------------
def _blit_slice(canvas, img, offset):
    w = img.width
    for x in range(PANEL_WIDTH):
        src_x = (offset + x) % w
        for y in range(PANEL_HEIGHT):
            r, g, b = img.getpixel((src_x, y))
            canvas.SetPixel(x, y, r, b, g)   # RBG panels: swap G and B


# ---------------------------------------------------------------------------
# Text overlay (drawn on top of the blitted PIL layer)
# ---------------------------------------------------------------------------
def _draw_overlay(canvas, cells, scroll_x):
    total_w = GAME_WIDTH * len(cells)

    for i, cell in enumerate(cells):
        bx = i * GAME_WIDTH - scroll_x
        for wrap in [0, total_w]:
            x = bx + wrap
            if x + GAME_WIDTH < 0 or x >= PANEL_WIDTH:
                continue
            if cell["type"] == "team_info":
                _draw_team_info(canvas, cell, x)
            else:
                _draw_player(canvas, cell, x)


def _draw_team_info(canvas, cell, x):
    """
    Layout (64 × 32 px cell):
      y= 8  │ Owner display name      (yellow)
      y=17  │ Fantasy team name       (white)
      y=28  │ 144.0-134.3 score line  (green if winning, red if losing)
    """
    score_color = _COLOR_GREEN if cell["winning"] else Colors.RED.value

    graphics.DrawText(canvas, font_small, x + 2, 8,
                      _rbg(Colors.YELLOW.value),
                      cell["owner"][:12])

    graphics.DrawText(canvas, font_small, x + 2, 17,
                      _rbg(Colors.WHITE.value),
                      _team_label(cell["team_name"]))

    score_line = f"{_fmt_pts(cell['points'])}-{_fmt_pts(cell['opp_points'])}"
    graphics.DrawText(canvas, font_small, x + 2, 28,
                      _rbg(score_color),
                      score_line)


def _draw_player(canvas, cell, x):
    """
    Layout (64 × 32 px cell):
      Left 14 px  │ NFL team logo (rendered in PIL layer)
      x+17, y=13  │ Player name — white / yellow (Q) / red (Out/IR)
      x+17, y=26  │ "POS  pts"
      top-right   │ injury indicator letter (Q / D / X)
    """
    injury = cell.get("injury")

    # Name color reflects injury severity
    if injury in ("Out", "IR"):
        name_color = Colors.RED.value
    elif injury in ("Questionable", "Doubtful"):
        name_color = Colors.YELLOW.value
    else:
        name_color = Colors.WHITE.value

    graphics.DrawText(canvas, font_small, x + TEXT_X, 13,
                      _rbg(name_color), cell["name"])

    # Injury indicator letter in top-right corner of the cell
    if injury:
        ind_map   = {"Questionable": "Q", "Doubtful": "D", "Out": "X", "IR": "IR"}
        indicator = ind_map.get(injury, "?")
        ind_color = Colors.YELLOW.value if injury in ("Questionable", "Doubtful") else Colors.RED.value
        graphics.DrawText(canvas, font_small, x + GAME_WIDTH - 10, 7,
                          _rbg(ind_color), indicator)

    # Position + fantasy points
    pts_line = f"{cell['position']} {_fmt_pts(cell['points'])}"
    graphics.DrawText(canvas, font_small, x + TEXT_X, 26,
                      _rbg(Colors.WHITE.value), pts_line)


# ---------------------------------------------------------------------------
# Public entry point — call from the main render loop
# ---------------------------------------------------------------------------
def draw_frame(canvas):
    global _data, _last_fetch, _cells
    global _virtual_canvas, _virtual_dirty, _scroll_x, _tick

    now = time()

    # Refresh data on interval
    if now - _last_fetch > FETCH_INTERVAL or _data is None:
        fresh = _fetch()
        if fresh:
            _data         = fresh
            _cells        = _build_cells(_data)
            _virtual_dirty = True
        _last_fetch = now

    if not _cells:
        canvas.Clear()
        graphics.DrawText(canvas, font, 8, 20,
                          _rbg(Colors.RED.value), "No fantasy")
        return canvas

    # Rebuild PIL background layer when data changes
    if _virtual_dirty or _virtual_canvas is None:
        result = _build_virtual_canvas(_cells)
        if result:
            _virtual_canvas, _ = result
        _virtual_dirty = False
        _scroll_x = 0

    total_scroll_w = GAME_WIDTH * len(_cells)

    canvas.Clear()

    if _virtual_canvas:
        _blit_slice(canvas, _virtual_canvas, _scroll_x)

    _draw_overlay(canvas, _cells, _scroll_x)

    # Advance scroll position
    _tick += 1
    if _tick >= _frames_per_tick:
        _tick = 0
        _scroll_x = (_scroll_x + _scroll_speed) % total_scroll_w

    return canvas