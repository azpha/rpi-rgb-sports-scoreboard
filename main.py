from scoreboard import ScoreboardMatrix
from time import sleep

# modes
from modes import score

scoreboard_matrix = ScoreboardMatrix()

def main():
  while True:
    if scoreboard_matrix.current_slide == "score":
      score.draw_frame(scoreboard_matrix)

    sleep(2)

main()