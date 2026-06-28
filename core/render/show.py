import cv2


def show(name: str, frame: cv2.typing.MatLike) -> int:
    cv2.imshow(name, frame)
    return cv2.waitKey(1)
