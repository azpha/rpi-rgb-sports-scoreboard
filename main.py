from scoreboard import ScoreboardMatrix
from time import sleep

# modes
from modes import score, fantasy

scoreboard_matrix = ScoreboardMatrix()

def main():
  while True:
    if scoreboard_matrix.current_slide == "score":
      canvas = score.draw_frame(scoreboard_matrix)
      if not canvas:
        scoreboard_matrix.canvas.Clear()
        scoreboard_matrix.canvas = scoreboard_matrix.matrix.SwapOnVSync(scoreboard_matrix.canvas)
        scoreboard_matrix.current_slide = "fantasy"
      else:
        scoreboard_matrix.canvas = scoreboard_matrix.matrix.SwapOnVSync(canvas)
    elif scoreboard_matrix.current_slide == "fantasy":
      canvas = fantasy.draw_frame(scoreboard_matrix)
      if not canvas:
        scoreboard_matrix.canvas.Clear()
        scoreboard_matrix.canvas = scoreboard_matrix.matrix.SwapOnVSync(scoreboard_matrix.canvas)
        scoreboard_matrix.current_slide = "score"
      else:
        scoreboard_matrix.canvas = scoreboard_matrix.matrix.SwapOnVSync(canvas)

    sleep(0.1)

main()