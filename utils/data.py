import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
ASSET_DIR = os.path.join(SCRIPT_DIR, "../assets")
LOGO_DIR = os.path.join(ASSET_DIR, "logos")