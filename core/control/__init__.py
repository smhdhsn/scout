"""
core.control — drone control: the API an agent calls, and the machinery that
actually drives the game.

================================================================================
OWNERSHIP — read this first
================================================================================
Claude Code maintains this package. The intent (from the project owner):

    "The control module is yours to manage. I'm not going to maintain it,
     because when I move on to actually building the drone pilot I want to
     just import a clean API and fly — not redo all these acrobatic moves to
     read game state and synthesize key presses every time."

So the contract is: everything below the `Drone` API is plumbing that exists to
keep that API clean. When this package changes, the goal is to *preserve the
Drone surface* (or improve it) so the future pilot code never has to think about
keyboards, daemons, or calibration. If you're Claude Code reading this later:
keep the layering intact, keep the docstrings honest, and keep `Drone` the only
thing a caller needs to learn.

================================================================================
WHAT THIS PACKAGE DOES
================================================================================
The game (FPV.SkyDive) is flown with the keyboard. An agent thinks in terms of
"throttle to 40%, flip forward, yaw 90° right" — not "hold the W key for 1.2s".
This package bridges that gap: it turns high-level setpoints into the timed,
streamed key presses the game expects, open-loop (no screen reading) and
approximate.

================================================================================
THE LAYERS  (low level -> high level)
================================================================================
input.py       ControlInput — the data. One immutable control frame
               (throttle / roll / pitch / yaw), values clamped to valid range.
               This is the vocabulary every layer speaks.

controller.py  Controller — the interface (Protocol). "Given a ControlInput,
               make it happen in the game." Defines send/reset/close so the
               driving mechanism is swappable (keyboard now, gamepad/API later).

keyboard.py    KeyboardController — the concrete driver. Implements Controller by
               *timing* key holds. Handles the two ways the game reads a held key:
               "level" axes (throttle) that hold their value when released, and
               "rate" axes (pitch/roll/yaw in acro) that command a rotation rate
               while held. This is where calibration and macOS key synthesis live.

daemon.py      ControlDaemon — the heartbeat. A background thread that re-sends
               the latest frame to the controller at a fixed rate, so a command
               *holds* until changed. Callers set a target once; they don't have
               to keep re-issuing it.

drone.py       Drone — THE API. The only thing a caller should need. Wraps the
               controller + daemon behind plain methods (set_throttle, pitch_by,
               flip, hover, ...). Start streaming, issue setpoints, done.

================================================================================
HOW THEY FIT TOGETHER
================================================================================
    agent -> Drone.set_throttle(0.4)          # high-level setpoint
               |  stores target ControlInput
               v
            ControlDaemon  (60 Hz thread)      # keeps the target alive
               |  every tick: send(target)
               v
            KeyboardController                  # ControlInput -> key presses
               |  press/release timed keys
               v
            FPV.SkyDive (must be focused)

Typical use:

    from core.control import Drone

    with Drone() as drone:          # starts the streaming daemon
        drone.set_throttle(0.40)    # ~40% throttle, then holds
        drone.flip()                # one full front flip, blocks until done
        drone.hover()               # stop rotating, keep throttle
    # all keys released on exit

================================================================================
THINGS THAT WILL BITE YOU
================================================================================
- Open-loop & approximate. There's no feedback from the game; rotations rely on
  calibrated rates (see keyboard.py / drone.py) and are accurate to ±~10°.
- Focus matters. Synthesized keys go to whatever window is focused, so the GAME
  must be the frontmost app while commands stream.
- macOS Accessibility permission is required for key synthesis.
- Keymap must match the game's bindings (see DEFAULT_KEYMAP in keyboard.py).
"""

from .controller import Controller
from .daemon import ControlDaemon
from .drone import Drone
from .input import ControlInput
from .keyboard import KeyboardController

__all__ = [
    "Controller",
    "ControlDaemon",
    "ControlInput",
    "Drone",
    "KeyboardController",
]
