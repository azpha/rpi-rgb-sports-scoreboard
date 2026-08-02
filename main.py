from scoreboard import ScoreboardMatrix
from time import sleep

# modes
from modes import score

scoreboard_matrix = ScoreboardMatrix()

def main():
  while True:
    print(scoreboard_matrix.current_slide)
    if scoreboard_matrix.current_slide == "score":
      canvas = score.draw_frame(scoreboard_matrix)
      print(canvas)
      if not canvas:
        scoreboard_matrix.current_slide = "fantasy"
      if canvas:
        scoreboard_matrix.canvas = scoreboard_matrix.matrix.SwapOnVSync(canvas)

    sleep(0.5)

main()