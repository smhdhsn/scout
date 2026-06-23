from __future__ import annotations

from dataclasses import dataclass


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class ControlInput:
    """One control frame the agent sends to the drone.

    Values are clamped on creation:
      - throttle:          0.0 (idle) .. 1.0 (full)
      - roll, pitch, yaw: -1.0 .. 1.0, 0.0 centered
    """

    throttle: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "throttle", _clamp(self.throttle, 0.0, 1.0))
        object.__setattr__(self, "roll", _clamp(self.roll, -1.0, 1.0))
        object.__setattr__(self, "pitch", _clamp(self.pitch, -1.0, 1.0))
        object.__setattr__(self, "yaw", _clamp(self.yaw, -1.0, 1.0))

    @classmethod
    def neutral(cls) -> "ControlInput":
        """Safe resting state: throttle idle, sticks centered."""
        return cls()
