import os
import requests
from PIL import Image
from io import BytesIO

LEAGUES = [
    ("hockey", "nhl"),
    ("football", "nfl"),
    ("basketball", "nba"),
    ("baseball", "mlb"),
]

LOGO_SIZE = (16, 16)

os.makedirs("./assets/logos", exist_ok=True)


def download_logos(sport, league):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    teams = resp.json().get("sports", [])[0].get("leagues", [])[0].get("teams", [])

    for entry in teams:
        team = entry["team"]
        abbr = team["abbreviation"].upper()
        logo_url = team.get("logos", [{}])[0].get("href")

        if not logo_url:
            print(f"No logo for {abbr}, skipping")
            continue
        if os.path.exists(os.path.join("./assets/logos", f"{league}_{abbr}.png")):
            print(f"Logo exists for {abbr}, skipping")
            continue

        try:
            img_resp = requests.get(logo_url, timeout=10)
            img = Image.open(BytesIO(img_resp.content)).convert("RGBA")

            # Resize to 16x16
            img = img.resize(LOGO_SIZE, Image.LANCZOS)

            # Flatten onto black background
            background = Image.new("RGB", LOGO_SIZE, (0, 0, 0))
            background.paste(img, mask=img.split()[3])

            out_path = os.path.join("./assets/logos", f"{league}_{abbr}.png")
            background.save(out_path)
            print(f"Saved {out_path}")
        except Exception as e:
            print(f"Error downloading {abbr}: {e}")


for sport, league in LEAGUES:
    print(f"\nDownloading {league.upper()} logos...")
    download_logos(sport, league)

print("\nDone!")
