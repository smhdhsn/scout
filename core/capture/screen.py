import mss
import numpy as np


class Screen:
    def __init__(self, monitor: int = 1):
        self._capturer = mss.mss()
        self._monitor = self._capturer.monitors[monitor]

    def grab(self) -> np.ndarray:
        raw = self._capturer.grab(self._monitor)

        sliced_img = np.array(raw)[:, :, :3]

        return np.ascontiguousarray(sliced_img)

    def close(self):
        self._capturer.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
