"""Status-file ingestion for Claude session state and tool prompt details."""

import json
from dataclasses import dataclass, field
from pathlib import Path
import time

from .app_logging import logger
from .constants import PENDING_INFER_SEC, STATUS_DIR, STATUS_STALE_SEC
from .host import normalize_tty_name


@dataclass
class StatusSnapshot:
    """One pass of derived slot status plus scroll-cache invalidation data."""

    slot_status: dict[int, str] = field(default_factory=dict)
    slot_hook_cwd: dict[int, str] = field(default_factory=dict)
    slot_tool_info: dict[int, dict] = field(default_factory=dict)
    clear_scroll_slots: set[int] = field(default_factory=set)
    reset_scroll_slots: set[int] = field(default_factory=set)


class StatusReader:
    """Read and normalize per-session status files written by hooks."""

    def normalize_tool_info(self, raw):
        """Normalize raw tool metadata into a compact common shape."""
        if raw in (None, "", {}):
            return None

        if isinstance(raw, str):
            stripped = raw.strip()
            if not stripped:
                return None
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError:
                return {"tool_name": "Tool", "tool_input": stripped}

        if not isinstance(raw, dict):
            return {"tool_name": "Tool", "tool_input": raw}

        tool_name = raw.get("tool_name") or raw.get("tool") or raw.get("name")
        tool_input = raw.get("tool_input")

        if tool_input is None:
            if "input" in raw:
                tool_input = raw["input"]
            elif "toolInput" in raw:
                tool_input = raw["toolInput"]

        if tool_name is None and isinstance(raw.get("tool"), dict):
            tool_name = raw["tool"].get("name")

        if tool_name is None and len(raw) == 1:
            only_key, only_value = next(iter(raw.items()))
            tool_name = str(only_key)
            tool_input = only_value

        if tool_name is None:
            tool_name = "Tool"

        if tool_input is None:
            tool_input = {
                key: value
                for key, value in raw.items()
                if key not in {"tool_name", "tool", "name", "input", "tool_input", "toolInput"}
            } or None

        return {"tool_name": str(tool_name), "tool_input": tool_input}

    def extract_hook_cwd(self, raw):
        """Extract hook-reported cwd from a raw hook payload, if present."""
        if raw in (None, "", {}):
            return None

        if isinstance(raw, str):
            stripped = raw.strip()
            if not stripped:
                return None
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError:
                return None

        if not isinstance(raw, dict):
            return None

        cwd = raw.get("cwd")
        if isinstance(cwd, str):
            cwd = cwd.strip()
            return cwd or None
        return None

    def read(self, slot_tty, config, formatter, scroll_text):
        """Read status files and return the current per-slot snapshot."""
        status_dir = Path(STATUS_DIR)
        snapshot = StatusSnapshot()
        if not status_dir.exists():
            return snapshot

        now = time.time()
        idle_timeout = config.get("idle_timeout", STATUS_STALE_SEC)
        tty_to_slot = {tty: slot for slot, tty in slot_tty.items()}

        for file_path in status_dir.iterdir():
            if file_path.name.startswith("."):
                continue
            try:
                data = json.loads(file_path.read_text())
            except (json.JSONDecodeError, IOError) as exc:
                logger.debug("Skipping status file: %s", exc)
                continue

            tty = normalize_tty_name(data.get("tty", file_path.name))
            slot = tty_to_slot.get(tty)
            if slot is None:
                continue

            ts = data.get("ts", 0)
            state = data.get("state", "unknown")
            age = now - ts

            if idle_timeout and state not in ("permission", "pending") and age > idle_timeout:
                continue

            if state == "pending":
                state = "permission" if age >= PENDING_INFER_SEC else "working"

            snapshot.slot_status[slot] = state

            hook_cwd = self.extract_hook_cwd(data.get("hook_input"))
            if hook_cwd is not None:
                snapshot.slot_hook_cwd[slot] = hook_cwd

            tool_info = self.normalize_tool_info(data.get("tool_input"))
            if tool_info is not None:
                snapshot.slot_tool_info[slot] = tool_info

        permission_slots = {
            slot for slot, state in snapshot.slot_status.items() if state == "permission"
        }
        snapshot.clear_scroll_slots = set(scroll_text) - permission_slots

        for slot in permission_slots:
            text = formatter(snapshot.slot_tool_info.get(slot))
            if scroll_text.get(slot) != text:
                snapshot.reset_scroll_slots.add(slot)

        return snapshot
