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

  def load_logo_to_image(self, league, abbr, width, height, x_offset, y_offset):
    key = f"{league}_{abbr}.png"
    logo_path = os.path.join(vars.LOGOS_DIR, key)
    if not os.path.exists(logo_path):
      return None
    
    if key in self.logo_cache:
      loaded_image = self.logo_cache[key]
    else:
      loaded_image = Image.open(logo_path).convert("RGB")
      self.logo_cache[key] = loaded_image
    
    image = Image.new("RGB", (width, height), (0,0,0))
    image.paste(loaded_image.resize((width, height), (x_offset, y_offset)))

    return image

  def iterate_slide_count(self):
    self.slide_count += 1

  def next_slide(self, slide_name):
    self.slide_count = 0
    self.current_slide = slide_name

  