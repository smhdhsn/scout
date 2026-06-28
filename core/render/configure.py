import cv2


def configure_window(name: str, *, size: tuple[int, int] = (480, 270)):
    w, h = size

    cv2.namedWindow(name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(name, cv2.WND_PROP_TOPMOST, 1)
    cv2.resizeWindow(name, w, h)
    cv2.moveWindow(name, 0, 0)
