import cv2

from core.capture import Screen
from core.navigation import decide
from core.perceive import find_gate
from core.render import configure_window, draw_rect, show
from core.window import find_window

GAME = "FPV.SkyDive"
APP_NAME = "Scout"


def main() -> None:
    screen = Screen(window=find_window(GAME))
    configure_window(APP_NAME)

    while True:
        frame = screen.capture()
        rect = find_gate(frame)
        action = decide(rect, frame.shape[1])

        print(f"Go {action}")

        if rect is not None:
            draw_rect(frame, rect)

        if show(APP_NAME, frame) == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
