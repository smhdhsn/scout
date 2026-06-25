from __future__ import annotations

import threading
import time
from dataclasses import replace

from core.control.controller import Controller
from core.control.daemon import ControlDaemon
from core.control.input import ControlInput
from core.control.keyboard import KeyboardController

# Degrees per second each rotation axis turns at full-rate command. Used to turn
# "rotate N degrees" into a hold duration (a full flip/roll/spin is 360°).
# Each value is a single rate (both directions the same) OR a
# (negative_dir, positive_dir) pair when one direction is faster — e.g.
# "pitch": (520.0, 510.0) means pitch-down (back flip) 520, pitch-up (front) 510.
# Tuned against the game; open-loop, so treat as close-enough. Calibration notes
# live inline in the comments beside each value — re-tune there if the game drifts.
DEFAULT_ROTATION_RATES: dict[str, float | tuple[float, float]] = {
    "pitch": 510.0,  # calibrated: a 360 front flip looks right
    "roll": 595.0,  # calibrated: 360 command did ~420 -> 510 * 420/360
    "yaw": 490.0,  # calibrated: 180 command did ~300 -> 294 * 300/180
}


class Drone:
    """The control API an agent calls to fly the drone.

    Wraps the proportional controller and the background daemon behind plain
    methods. The daemon keeps streaming the latest command to the game at a
    fixed rate, so a call like `set_throttle(0.4)` takes effect and *holds*
    until the next call — the agent issues setpoints, it does not have to keep
    re-sending them.

    Axis conventions (same as ControlInput), and how they behave in acro:
        throttle        0.0 .. 1.0     a held LEVEL — set it and it stays
        roll/pitch/yaw -1.0 .. 1.0     a rotation RATE — non-zero keeps the drone
                                       rotating; 0.0 stops it, attitude holds

    Two ways to drive the rotation axes:
      - `set_pitch(0.4)` etc. command a continuous rate (keeps rotating until you
        change it) — good for closed-loop / live steering.
      - `pitch_by(90)`, `roll_by(360)`, `yaw_by(180)`, `flip()` rotate a fixed
        number of degrees and stop. Blocking: returns when the turn completes.

    Control is open-loop and approximate (no screen reading). The GAME must be the
    focused app while commands stream (synthesized keys go to the focused window).

    Example:
        with Drone() as drone:          # starts streaming on enter
            drone.set_throttle(0.40)    # ~40% throttle, then holds
            drone.pitch_by(20)          # nose down 20°, then hold the attitude
            drone.flip()                # one full front flip
            drone.hover()               # stop rotating, keep throttle
        # keys released on exit
    """

    def __init__(
        self,
        controller: Controller | None = None,
        hz: int = 60,
        rotation_rates: dict[str, float | tuple[float, float]] | None = None,
    ):
        self._controller = controller or KeyboardController()
        self._daemon = ControlDaemon(self._controller, hz=hz)
        self._rates = rotation_rates or dict(DEFAULT_ROTATION_RATES)
        self._target = ControlInput.neutral()
        self._lock = threading.Lock()
        self._started = False

    # ---- lifecycle ----------------------------------------------------

    def start(self) -> "Drone":
        """Begin streaming commands to the game."""
        if not self._started:
            self._daemon.start()
            self._started = True
        return self

    def stop(self) -> None:
        """Stop streaming and release every held key."""
        if self._started:
            self._daemon.stop()
            self._started = False

    def __enter__(self) -> "Drone":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    # ---- absolute setpoints -------------------------------------------

    def set(
        self,
        *,
        throttle: float | None = None,
        roll: float | None = None,
        pitch: float | None = None,
        yaw: float | None = None,
    ) -> ControlInput:
        """Set one or more axes to absolute targets; omitted axes are unchanged.

        Returns the resulting command frame (values clamped to valid range).
        """
        updates = {
            axis: value
            for axis, value in (
                ("throttle", throttle),
                ("roll", roll),
                ("pitch", pitch),
                ("yaw", yaw),
            )
            if value is not None
        }
        with self._lock:
            self._target = replace(self._target, **updates)
            self._daemon.set(self._target)
            return self._target

    def set_throttle(self, value: float) -> ControlInput:
        return self.set(throttle=value)

    def set_roll(self, value: float) -> ControlInput:
        return self.set(roll=value)

    def set_pitch(self, value: float) -> ControlInput:
        return self.set(pitch=value)

    def set_yaw(self, value: float) -> ControlInput:
        return self.set(yaw=value)

    # ---- relative nudges ----------------------------------------------

    def adjust(
        self,
        *,
        throttle: float = 0.0,
        roll: float = 0.0,
        pitch: float = 0.0,
        yaw: float = 0.0,
    ) -> ControlInput:
        """Nudge axes by relative deltas; result clamps to valid range."""
        with self._lock:
            t = self._target
            self._target = replace(
                t,
                throttle=t.throttle + throttle,
                roll=t.roll + roll,
                pitch=t.pitch + pitch,
                yaw=t.yaw + yaw,
            )
            self._daemon.set(self._target)
            return self._target

    # ---- timed rotations (degrees) ------------------------------------

    def rotate_by(self, axis: str, degrees: float) -> None:
        """Rotate `axis` ('pitch'|'roll'|'yaw') by ~`degrees` at full rate, then
        stop — acro holds the resulting attitude. Sign sets direction.

        Blocking: returns once the turn completes. Open-loop, so accuracy tracks
        the calibration in `rotation_rates` and timing jitter (±~10°).
        """
        positive = degrees >= 0
        rate = self._rate_for(axis, positive)
        duration = abs(degrees) / rate if rate else 0.0
        self.set(**{axis: 1.0 if positive else -1.0})  # full-rate rotation
        time.sleep(duration)
        self.set(**{axis: 0.0})  # stop; attitude holds

    def _rate_for(self, axis: str, positive: bool) -> float:
        """Look up the rotation rate for an axis, honoring a per-direction
        (negative_dir, positive_dir) pair if one is configured."""
        rate = self._rates[axis]
        if isinstance(rate, (tuple, list)):
            negative_rate, positive_rate = rate
            return positive_rate if positive else negative_rate
        return rate

    def pitch_by(self, degrees: float) -> None:
        """Pitch (nose up/down) by `degrees`. Positive = the `up` key's direction."""
        self.rotate_by("pitch", degrees)

    def roll_by(self, degrees: float) -> None:
        """Roll (bank) by `degrees`. Positive = the `right` key's direction."""
        self.rotate_by("roll", degrees)

    def yaw_by(self, degrees: float) -> None:
        """Yaw (spin flat) by `degrees`. Positive = the `d` key's direction."""
        self.rotate_by("yaw", degrees)

    def flip(self) -> None:
        """One full 360° front flip (pitch)."""
        self.pitch_by(360.0)

    # ---- convenience ---------------------------------------------------

    def hover(self) -> ControlInput:
        """Center roll/pitch/yaw, keep the current throttle."""
        return self.set(roll=0.0, pitch=0.0, yaw=0.0)

    def neutral(self) -> ControlInput:
        """All axes to rest: throttle idle, sticks centered."""
        with self._lock:
            self._target = ControlInput.neutral()
            self._daemon.set(self._target)
            return self._target

    # ---- introspection -------------------------------------------------

    @property
    def target(self) -> ControlInput:
        """The command currently being streamed to the game."""
        with self._lock:
            return self._target

    @property
    def estimate(self) -> ControlInput:
        """Best guess of where the drone's axes actually sit (open-loop)."""
        estimates = getattr(self._controller, "estimates", None)
        return estimates() if estimates is not None else self.target
