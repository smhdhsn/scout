import numpy as np
import Quartz

from core.models import Window


class Screen:
    def __init__(self, window: Window):
        self._window_id = window.window_id

    def capture(self) -> np.ndarray:
        image = Quartz.CGWindowListCreateImage(
            Quartz.CGRectNull,
            Quartz.kCGWindowListOptionIncludingWindow,
            self._window_id,
            Quartz.kCGWindowImageBoundsIgnoreFraming,
        )

        return _cgimage_to_bgr(image)


def _cgimage_to_bgr(image) -> np.ndarray:
    width = Quartz.CGImageGetWidth(image)
    height = Quartz.CGImageGetHeight(image)
    bytes_per_row = Quartz.CGImageGetBytesPerRow(image)

    data = Quartz.CGDataProviderCopyData(Quartz.CGImageGetDataProvider(image))

    buffer = np.frombuffer(data, dtype=np.uint8)
    pixels = buffer.reshape((height, bytes_per_row // 4, 4))

    return np.ascontiguousarray(pixels[:, :width, :3])
