from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image
import os
import vars

class ScoreboardMatrix():
  logo_cache = {}
  current_slide = "score"
  slide_count = 0
  options = RGBMatrixOptions()
  options.rows = 32
  options.cols = 64
  options.chain_length = 4
  options.parallel = 1
  options.hardware_mapping = "regular"
  options.gpio_slowdown = 5
  options.disable_hardware_pulsing = True
  options.brightness = 80

  matrix = RGBMatrix(options=options)
  canvas = matrix.CreateFrameCanvas()

  def load_logo(self, league, abbr):
      key = f"{league}_{abbr}"
      if key in self.logo_cache:
          return self.logo_cache[key]

      path = os.path.join(vars.LOGO_DIR, f"{key}.png")
      if not os.path.exists(path):
          print(f"Logo not found: {path}")
          self.logo_cache[key] = None
          return None

      try:
          # FIX: convert to RGB here so draw_logo always gets 3-channel pixels
          img = Image.open(path).convert("RGB")
          self.logo_cache[key] = img
          return img
      except Exception as e:
          print(f"Error loading logo {key}: {e}")
          self.logo_cache[key] = None
          return None

  def iterate_slide_count(self):
    self.slide_count += 1

  def next_slide(self, slide_name):
    self.slide_count = 0
    self.current_slide = slide_name

  