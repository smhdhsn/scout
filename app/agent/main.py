import cv2

from core.capture import Screen
from core.window import find_window


def main():
    game_window = find_window("FPV.SkyDive")

    screen = Screen(game_window)

    img = screen.capture()

    cv2.imshow("unknown", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
