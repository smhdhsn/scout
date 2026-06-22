from core.capture import Screen
import cv2


def main():
    screen = Screen()

    img = screen.grab()

    screen.close()


if __name__ == "__main__":
    main()
