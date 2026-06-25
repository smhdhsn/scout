import cv2
import numpy as np

from core.capture import Screen
from core.window import find_window

LOWER = np.array([45, 80, 80])
UPPER = np.array([85, 255, 255])

Box = tuple[int, int, int, int]

Action = str

GAME = "FPV.SkyDive"


def main() -> None:
    screen = Screen(window=find_window(GAME))
    open_preview()

    while True:
        frame = screen.capture()
        box = perceive(frame)
        action = decide(box, frame.shape[1])

        print(f"Go {action}")

        annotate(frame, box)

        if not render(frame):
            break

    cv2.destroyAllWindows()


def perceive(frame: cv2.typing.MatLike) -> Box | None:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, LOWER, UPPER)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    biggest = max(contours, key=cv2.contourArea)

    return cv2.boundingRect(biggest)


DEADZONE = 100


def decide(box: Box | None, frame_width: int) -> Action:
    if box is None:
        return "Search"

    x, _, w, _ = box

    gate_center_x = x + w // 2
    frame_center_x = frame_width // 2
    error = gate_center_x - frame_center_x

    if abs(error) < DEADZONE:
        return "forward"

    match error:
        case e if e > 0:
            return "right"
        case e if e < 0:
            return "left"


def annotate(frame: cv2.typing.MatLike, box: Box):
    if box is None:
        print("gate: none")
        return

    x, y, w, h = box
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 5)

    print(f"gate: x:{x}, y:{y}, w:{w}, h:{h}")


def render(frame: cv2.typing.MatLike) -> bool:
    cv2.imshow("Game", frame)
    return cv2.waitKey(1) & 0xFF != ord("q")


def open_preview():
    cv2.namedWindow("Game", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Game", cv2.WND_PROP_TOPMOST, 1)
    cv2.resizeWindow("Game", 480, 270)
    cv2.moveWindow("Game", 0, 0)


if __name__ == "__main__":
    main()
