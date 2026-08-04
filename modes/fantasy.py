import requests
from PIL import Image
from time import time
from rgbmatrix import graphics
from vars import PANEL_HEIGHT, PANEL_WIDTH, GAME_WIDTH, DIVIDER_COLOR, Colors, font, font_small, font_super_small

players = {
    "team1": [],
    "team2": []
}
team_info = {
    "team1": {},
    "team2": {}
}
last_fetch = 0

STATIC_CARD_WIDTH = 96
SCROLL_REGION_X = STATIC_CARD_WIDTH
SCROLL_REGION_WIDTH = PANEL_WIDTH - STATIC_CARD_WIDTH

# BDF fonts here are fixed-width bitmap fonts named "<char_width>x<char_height>.bdf"
SMALL_CHAR_WIDTH = 5   # 5x7.bdf
SUPER_SMALL_CHAR_WIDTH = 4  # 4x6.bdf
STATIC_CARD_MARGIN = 4

scroll_x = 0
scroll_speed = 1
frames_per_tick = 1
tick = 0
times_scrolled = 0
virtual_canvas = None
virtual_dirty = True
current_team = "team1"

def rbg(color_tuple):
    r, g, b = color_tuple
    return graphics.Color(r, b, g)

def fetch_data():
    try:
        resp = requests.get("https://api.alexav.gg/v4/sports/fantasy", timeout=5)
        resp.raise_for_status()
        data = resp.json()

        new_players = {"team1": [], "team2": []}
        new_team_info = {"team1": {}, "team2": {}}
        for key in ("team1", "team2"):
          for player in data[key]["players"]:
            new_players[key].append({
                "first_name": player['first_name'],
                "last_name": player['last_name'],
                "abbr_name": f"{player['first_name'][0]}. {player['last_name']}",
                "position": player['position'],
                "team": player['team'],
                "injury_status": "Q" if player.get('injury_status') == "Questionable" else player.get('injury_status'),
                "injury_body_part": player.get('injury_body_part')
            })

          owner = data[key].get("owner") or {}
          metadata = owner.get("metadata") or {}
          new_team_info[key] = {
              "name": metadata.get("team_name") or owner.get("display_name") or key.upper(),
              "points": data[key].get("points"),
          }

        return new_players, new_team_info
    except Exception as e:
        print(f"[fantasy] fetch error: {e}")
        return None, None

def _wrap_to_width(text, char_width, max_width, max_lines):
    """Word-wrap text into at most max_lines lines that each fit within
    max_width pixels, assuming a fixed-width font. Overlong single words are
    hard-truncated so nothing ever overflows the given width."""
    max_chars = max(1, max_width // char_width)

    lines = []
    current = ""
    for word in text.split(" "):
        if len(word) > max_chars:
            word = word[:max_chars]
        trial = f"{current} {word}".strip()
        if len(trial) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = trial
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)

    return [line[:max_chars] for line in lines[:max_lines]]

def draw_static_card(canvas, team):
    """Draw a fixed, non-scrolling card for the given team into the leftmost
    STATIC_CARD_WIDTH pixels of the canvas."""
    info = team_info.get(team, {})
    name = info.get("name") or team.upper()
    points = info.get("points")

    text_width = STATIC_CARD_WIDTH - STATIC_CARD_MARGIN - 3  # stay clear of the divider

    label = "TEAM 1" if team == "team1" else "TEAM 2"
    graphics.DrawText(canvas, font_small, STATIC_CARD_MARGIN, 8, rbg(Colors.YELLOW.value), label)

    name_lines = _wrap_to_width(name, SUPER_SMALL_CHAR_WIDTH, text_width, max_lines=2)

    y = 17
    for line in name_lines:
        graphics.DrawText(canvas, font_super_small, STATIC_CARD_MARGIN, y, rbg(Colors.WHITE.value), line)
        y += 7

    if points is not None:
        graphics.DrawText(canvas, font_small, STATIC_CARD_MARGIN, 30, rbg(Colors.RED.value), f"{points:.1f}")

    # divider on right edge of the static card
    r, g, b = DIVIDER_COLOR
    for row in range(PANEL_HEIGHT):
        canvas.SetPixel(STATIC_CARD_WIDTH - 1, row, r, b, g)

def draw_text_overlay(canvas, players, scroll_x, dest_x=0, width=PANEL_WIDTH):
    total_width = GAME_WIDTH * len(players)

    for i, player in enumerate(players):
        base_x = (i * GAME_WIDTH) - scroll_x

        # draw twice to handle the wrap-around copy
        for wrap in [0, total_width]:
            x = base_x + wrap

            # cull slots fully off the visible region
            if x + GAME_WIDTH < 0 or x >= width:
                continue

            x += dest_x

            graphics.DrawText(canvas, font, x + 35, 15,
                              rbg(Colors.WHITE.value), player['abbr_name'])
            graphics.DrawText(canvas, font_small, x + 35, 25,
                              rbg(Colors.WHITE.value), player['position'])

            if player['injury_status'] and player['injury_body_part']:
                graphics.DrawText(canvas, font_small, x + 50, 25,
                                rbg(Colors.RED.value), f"{str(player['injury_status'])} - ")
                graphics.DrawText(canvas, font_super_small, x + 70, 25,
                                rbg(Colors.RED.value), str(player["injury_body_part"]))

            # # if the time is shown it should be split between lines
            # # if not, just display the status
            # if "AM" in game["status"] or "PM" in game["status"]:
            #     game_status_split = game["status"].split("-")
            #     date = game_status_split[0].strip()
            #     time = game_status_split[1].strip()

            #     graphics.DrawText(canvas, font_small, x + 60, 10,
            #                     rbg(Colors.YELLOW.value), date)
            #     graphics.DrawText(canvas, font_small, x + 60, 20,
            #                     rbg(Colors.YELLOW.value), time)
            #     graphics.DrawText(canvas, font_small, x + 60, 30,
            #                     rbg(Colors.YELLOW.value), game["venue"])
            # else:
            #     graphics.DrawText(canvas, font_small, x + 65, 20,
            #                     rbg(Colors.YELLOW.value), game["status"])

def render_player(matrix, img, player, x_offset):
    league = "nfl"

    team_logo = matrix.load_logo(league, player['team'])
    if team_logo:
        img.paste(team_logo.resize((28, 28)), (x_offset, 0))

    # divider on right edge (except last slot handled by wrapping)
    for row in range(PANEL_HEIGHT):
        img.putpixel((x_offset + GAME_WIDTH - 1, row), DIVIDER_COLOR)

def build_canvas(matrix, team):
    print(players)
    total_players = len(players[team])
    total_width = GAME_WIDTH * (total_players + 4)
    img = Image.new("RGB", (total_width, PANEL_HEIGHT), (0,0,0))

    for i, player in enumerate(players[team] * 2):
        if i >= total_players + 4:
            break
        render_player(matrix, img, player, i * GAME_WIDTH)

    return img, total_players

def blit_slice(canvas, pil_img, x_offset, dest_x=0, width=PANEL_WIDTH):
    total_width = pil_img.width
    for x in range(width):
        src_x = (x_offset + x) % total_width
        for y in range(PANEL_HEIGHT):
            r, g, b = pil_img.getpixel((src_x, y))
            canvas.SetPixel(dest_x + x, y, r, b, g)

def draw_frame(matrix):
    global players, team_info, last_fetch, virtual_canvas, virtual_dirty, scroll_x, tick
    global total_players, current_team
    now = time()

    if now - last_fetch > 30 or not players['team1'] or not players['team2']:
        fetched_players, fetched_team_info = fetch_data()
        if fetched_players is not None:
            players = fetched_players
            team_info = fetched_team_info
        last_fetch = now
        virtual_dirty = True

    if virtual_dirty or virtual_canvas is None:
        result = build_canvas(matrix, current_team)
        if result:
            virtual_canvas, total_players = result
            virtual_dirty = False

    matrix.canvas.Clear()
    draw_static_card(matrix.canvas, current_team)

    if not len(players[current_team]) > 0:
        graphics.DrawText(matrix.canvas, font, GAME_WIDTH + 10, 22,
                          rbg(Colors.RED.value),
                          "No players")
        scroll_x = tick = 0
        return matrix.canvas

    total_scroll_width = GAME_WIDTH * len(players[current_team])
    if virtual_canvas:
        blit_slice(matrix.canvas, virtual_canvas, scroll_x, dest_x=SCROLL_REGION_X, width=SCROLL_REGION_WIDTH)
    draw_text_overlay(matrix.canvas, players[current_team], scroll_x, dest_x=SCROLL_REGION_X, width=SCROLL_REGION_WIDTH)

    tick += 1
    if tick >= frames_per_tick:
        tick = 0
        next_x = scroll_x + scroll_speed
        if next_x >= total_scroll_width:
            scroll_x = 0
            tick = 0

            if current_team == "team1":
                current_team = "team2"
                virtual_dirty = True
                return matrix.canvas
            else:
                current_team = "team1"
                virtual_dirty = True
                return None
        scroll_x = next_x

    return matrix.canvas