"""The heartbeat: a background thread that keeps the latest command alive.

The game needs commands streamed continuously (a held key, a pulsed rate). But
we want callers to issue a setpoint *once* and have it hold. The daemon bridges
that: it owns the "current" frame and re-sends it to the controller at a fixed
rate (default 60 Hz) on its own thread. Callers just swap the current frame via
`set()`; the thread does the repeating.

Thread-safety: `set()` (caller thread) and `_run()` (daemon thread) both touch
`_current`, so it's guarded by a lock. The frame itself is immutable, so we copy
the reference under the lock and send outside it — keeping the lock held only
for the instant of the swap.
"""

from __future__ import annotations

import threading
import time

from core.control.input import ControlInput


class ControlDaemon:
    def __init__(self, controller, hz: int = 60):
        self._controller = controller          # the driver we stream frames to
        self._period = 1.0 / hz                 # seconds between sends
        self._current = ControlInput.neutral()  # the frame being streamed now
        self._lock = threading.Lock()           # guards _current across threads
        self._stop = threading.Event()          # signals _run to exit
        self._thread: threading.Thread | None = None

    def set(self, control: ControlInput) -> None:
        """Swap the target frame the daemon keeps sending (called by caller)."""
        with self._lock:
            self._current = control

    def start(self) -> None:
        """Spin up the streaming thread. No-op if already running."""
        if self._thread is not None:
            return
        self._stop.clear()
        # daemon=True so the thread can't keep the process alive on its own.
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop streaming, join the thread, and release the controller."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._controller.reset()  # back to neutral
        self._controller.close()  # release every held input

    def _run(self) -> None:
        """Thread body: re-send the current frame every period until stopped."""
        while not self._stop.is_set():
            with self._lock:
                current = self._current  # snapshot under lock, send outside it
            self._controller.send(current)
            time.sleep(self._period)
