from __future__ import annotations

import time

from pynput.keyboard import Controller as _KeyboardController
from pynput.keyboard import Key, KeyCode

from core.control.input import ControlInput

# axis -> (key that DECREASES the value, key that INCREASES it).
# A single char -> that key; otherwise a pynput Key name (e.g. "up").
# THESE MUST MATCH FPV.SkyDive's keyboard bindings — change to suit.
DEFAULT_KEYMAP: dict[str, tuple[str, str]] = {
    "throttle": ("s", "w"),       # down / up
    "pitch": ("down", "up"),
    "roll": ("left", "right"),
    "yaw": ("a", "d"),
}

# Two ways the game treats a held key, so we drive two ways:
#
#   "level" — the value integrates and STAYS where you release the key
#             (throttle). Hold the key only long enough to reach the target,
#             then let go; the game keeps the value.
#
#   "rate"  — the key commands a rotation RATE (pitch/roll/yaw in acro). Holding
#             it keeps the drone rotating (that's how flips and spins happen);
#             releasing stops the rotation and the attitude holds. So the command
#             is a signed rate, and we keep the key engaged while it's non-zero,
#             pulsing it (PWM) so the magnitude sets the fraction of full rate.
DEFAULT_AXIS_KIND: dict[str, str] = {
    "throttle": "level",
    "pitch": "rate",
    "roll": "rate",
    "yaw": "rate",
}

# For "level" axes only: seconds of holding a key to sweep the value across its
# whole range. Calibrate against the game.
DEFAULT_RAMP_SECONDS: dict[str, float] = {
    "throttle": 2.4,  # calibrated: 2.27 read 46%, 2.5 read 53% for a 50% command
}

# Min/max each axis can reach (matches ControlInput clamping).
AXIS_RANGE: dict[str, tuple[float, float]] = {
    "throttle": (0.0, 1.0),
    "pitch": (-1.0, 1.0),
    "roll": (-1.0, 1.0),
    "yaw": (-1.0, 1.0),
}

# Parking deadband for "level" axes: how close the estimate must get before we
# release the key.
DEFAULT_TOLERANCE: dict[str, float] = {
    "throttle": 0.01,
}

# "rate" axes pulse the key within this window; duty = |command|. At 1.0 the key
# is held continuously (full rate / a flip); at 0.5 it's down ~half the time.
DEFAULT_PWM_PERIOD = 0.1


def _resolve(key: str):
    """'a' -> KeyCode('a');  'up' -> Key.up."""
    return KeyCode.from_char(key) if len(key) == 1 else getattr(Key, key)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class KeyboardController:
    """Proportional control by *timing* key holds, with two axis kinds.

    The game treats axes two ways, so we do too (see DEFAULT_AXIS_KIND):

    - "level" axes (throttle) integrate and HOLD when the key is released. We
      keep an estimate of where the axis sits and hold the up/down key only long
      enough to reach the target, then let go — so `throttle=0.41` settles near
      41% instead of running to 100%, and self-corrects on overshoot.

    - "rate" axes (pitch/roll/yaw, in acro) command a rotation RATE. Holding the
      key keeps the drone rotating — that is how a flip or a spin happens — and
      releasing stops it with the attitude held. We keep the key engaged while
      the command is non-zero and pulse it (PWM) at duty = |command|: 1.0 holds
      it down (full rate), 0.3 holds it ~30% of the time (gentle), 0.0 releases.
      The sign picks the direction.

    `send(target)` is called every tick by the daemon. Open-loop and approximate.

    Needs macOS Accessibility permission, and the GAME must be the focused app
    when keys are sent (synthesized keys go to whatever window has focus).
    """

    def __init__(
        self,
        keymap: dict[str, tuple[str, str]] | None = None,
        ramp_seconds: dict[str, float] | None = None,
        axis_kind: dict[str, str] | None = None,
        tolerance: float | dict[str, float] | None = None,
        pwm_period: float = DEFAULT_PWM_PERIOD,
    ):
        self._keymap = keymap or DEFAULT_KEYMAP
        self._ramp = ramp_seconds or DEFAULT_RAMP_SECONDS
        self._kind = axis_kind or DEFAULT_AXIS_KIND
        self._tolerance = self._resolve_tolerance(tolerance)
        self._pwm = pwm_period

        self._kb = _KeyboardController()
        self._held: set = set()
        # "level" axes track an estimate + the direction we drove it last tick;
        # "rate" axes just store the command being applied (for display).
        self._estimate: dict[str, float] = {axis: 0.0 for axis in self._keymap}
        self._direction: dict[str, int] = {axis: 0 for axis in self._keymap}
        self._last: float | None = None

    def send(self, target: ControlInput) -> None:
        now = time.monotonic()
        dt = 0.0 if self._last is None else now - self._last
        self._last = now

        # Advance the estimate for "level" axes by however far we drove them.
        self._integrate(dt)

        wanted: set = set()
        for axis, (neg_key, pos_key) in self._keymap.items():
            value = getattr(target, axis)
            if self._kind.get(axis, "level") == "rate":
                key = self._rate_key(axis, value, neg_key, pos_key, now)
            else:
                key = self._level_key(axis, value, neg_key, pos_key)
            if key is not None:
                wanted.add(key)

        for key in wanted - self._held:
            self._kb.press(key)
        for key in self._held - wanted:
            self._kb.release(key)
        self._held = wanted

    def reset(self) -> None:
        """Stop driving and release keys.

        "level" axes hold their value in-game, so this stops *controlling* rather
        than returning to neutral; set a neutral target and give the daemon time
        to drive throttle down. "rate" axes simply stop rotating once released.
        """
        for key in self._held:
            self._kb.release(key)
        self._held = set()
        self._direction = {axis: 0 for axis in self._keymap}

    def close(self) -> None:
        for key in self._held:
            self._kb.release(key)
        self._held = set()

    def estimates(self) -> ControlInput:
        """Best guess of each axis: tracked level for "level" axes, the command
        currently applied for "rate" axes. For display/logging."""
        return ControlInput(**self._estimate)

    def _resolve_tolerance(self, tolerance) -> dict[str, float]:
        """Accept None (per-axis defaults), one float (uniform), or a dict."""
        if tolerance is None:
            return dict(DEFAULT_TOLERANCE)
        if isinstance(tolerance, dict):
            return tolerance
        return {axis: float(tolerance) for axis in self._keymap}

    def _level_key(self, axis: str, target: float, neg_key: str, pos_key: str):
        """Drive a held-value axis toward `target`, then release within tolerance."""
        tol = self._tolerance.get(axis, 0.01)
        error = target - self._estimate[axis]
        if error > tol:
            self._direction[axis] = +1
            return _resolve(pos_key)
        if error < -tol:
            self._direction[axis] = -1
            return _resolve(neg_key)
        self._direction[axis] = 0  # within tolerance: hold position
        return None

    def _rate_key(self, axis: str, value: float, neg_key: str, pos_key: str, now: float):
        """Pulse a rotation axis at duty = |value| to set its rate; sign = direction."""
        self._estimate[axis] = value  # what we're applying, for display
        duty = min(abs(value), 1.0)
        if duty <= 0.0:
            return None
        phase = (now % self._pwm) / self._pwm
        if phase < duty:
            return _resolve(pos_key if value > 0 else neg_key)
        return None

    def _integrate(self, dt: float) -> None:
        if dt <= 0.0:
            return
        for axis, direction in self._direction.items():
            if direction == 0 or self._kind.get(axis, "level") != "level":
                continue
            lo, hi = AXIS_RANGE[axis]
            rate = (hi - lo) / self._ramp[axis]  # units per second
            self._estimate[axis] = _clamp(
                self._estimate[axis] + direction * rate * dt, lo, hi
            )
