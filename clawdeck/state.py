"""Mutable controller state shared between rendering and polling."""

from dataclasses import dataclass, field
import time

from .constants import MODE_ROW


@dataclass
class ControllerState:
    """Track transient controller state that should not live in config."""

    mode: str = MODE_ROW
    active_slot: int | None = None
    slot_tty: dict[int, str] = field(default_factory=dict)
    slot_cwd: dict[int, str] = field(default_factory=dict)
    slot_status: dict[int, str] = field(default_factory=dict)
    slot_tool_info: dict[int, dict] = field(default_factory=dict)
    scroll_offsets: dict[int, int] = field(default_factory=dict)
    scroll_images: dict[int, object] = field(default_factory=dict)
    scroll_text: dict[int, str] = field(default_factory=dict)
    blink_on: bool = True
    key_press_time: dict[int, float] = field(default_factory=dict)
    last_blink_toggle: float = field(default_factory=time.time)
    last_tty_refresh: float = 0
    last_active_cwd_check: float = 0
