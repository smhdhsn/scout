"""The driver interface: how a control frame becomes action in the game.

`Controller` is a Protocol (structural interface), not a base class — anything
with these three methods qualifies. It exists so the *mechanism* that drives the
game is swappable without touching the `Drone` API or the daemon above it:
`KeyboardController` is the only implementation today, but a gamepad emulator or
a direct game API could drop in here unchanged.

The daemon (daemon.py) holds a Controller and calls `send` every tick; the Drone
API (drone.py) never talks to a Controller directly.
"""

from __future__ import annotations

from typing import Protocol

from core.control.input import ControlInput


class Controller(Protocol):
    def send(self, control: ControlInput) -> None:
        """Apply one control frame to the game. Called once per daemon tick."""
        ...

    def reset(self) -> None:
        """Return to neutral (throttle idle, sticks centered, keys released)."""
        ...

    def close(self) -> None:
        """Release the device / all held inputs. Final cleanup on shutdown."""
        ...
