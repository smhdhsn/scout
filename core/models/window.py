from __future__ import annotations

from dataclasses import dataclass

from .rect import Rect


@dataclass(frozen=True)
class Window:
    owner: str
    window_id: int
    bounds: Rect
