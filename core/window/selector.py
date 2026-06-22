from __future__ import annotations

import Quartz

from core.models import Rect, Window


def find_window(owner_name: str) -> Window:
    all_windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionAll,
        Quartz.kCGNullWindowID,
    )

    game_windows = [
        window
        for window in all_windows
        if window.get("kCGWindowOwnerName") == owner_name
        and window.get("kCGWindowAlpha", 1) > 0
    ]

    return _to_window(
        max(game_windows, key=_area),
    )


def _area(window) -> float:
    bounds = window["kCGWindowBounds"]
    return bounds["Width"] * bounds["Height"]


def _to_window(window) -> Window:
    bounds = window["kCGWindowBounds"]

    rect = Rect(
        x=int(bounds["X"]),
        y=int(bounds["Y"]),
        width=int(bounds["Width"]),
        height=int(bounds["Height"]),
    )

    return Window(
        owner=window.get("kCGWindowOwnerName", ""),
        window_id=int(window.get("kCGWindowNumber", 0)),
        bounds=rect,
    )
