import cv2
import numpy as np

LOWER = np.array([45, 80, 80])
UPPER = np.array([85, 255, 255])


def find_gate(frame: cv2.typing.MatLike) -> cv2.typing.Rect | None:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, LOWER, UPPER)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    biggest = max(contours, key=cv2.contourArea)

    return cv2.boundingRect(biggest)
