from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Window:
    owner: str
    window_id: int
