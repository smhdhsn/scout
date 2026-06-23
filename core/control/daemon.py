from __future__ import annotations

import threading
import time

from core.control.input import ControlInput


class ControlDaemon:
    def __init__(self, controller, hz: int = 60):
        self._controller = controller
        self._period = 1.0 / hz
        self._current = ControlInput.neutral()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def set(self, control: ControlInput) -> None:
        """Set the target frame the daemon keeps sending."""
        with self._lock:
            self._current = control

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._controller.reset()
        self._controller.close()

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                current = self._current
            self._controller.send(current)
            time.sleep(self._period)
