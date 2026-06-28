import cv2


def draw_rect(
    frame: cv2.typing.MatLike,
    rect: cv2.typing.Rect,
    *,
    color: tuple[float, float, float] = (0.0, 0.0, 255.0),
    thickness: int = 5,
):
    x, y, w, h = rect
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
