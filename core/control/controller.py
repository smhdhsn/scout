from __future__ import annotations

from typing import Protocol

from core.control.input import ControlInput


class Controller(Protocol):
    def send(self, control: ControlInput) -> None:
        """Apply one control frame to the game."""
        ...

    def reset(self) -> None:
        """Return to neutral (throttle idle, sticks centered, keys released)."""
        ...

    def close(self) -> None:
        """Release the device / all held inputs."""
        ...
