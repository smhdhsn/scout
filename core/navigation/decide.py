import cv2

DEADZONE = 100


def decide(rect: cv2.typing.Rect | None, frame_width: int) -> str:
    if rect is None:
        return "Search"

    x, _, w, _ = rect

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
        case _:
            raise AssertionError(f"unreachable: error={error}")
