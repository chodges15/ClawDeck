import subprocess
import time

import CoreFoundation
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventGetFlags,
    CGEventGetIntegerValueField,
    CGEventPost,
    CGEventSetFlags,
    CGEventTapCreate,
    kCGEventFlagsChanged,
    kCGEventKeyDown,
    kCGHIDEventTap,
    kCGHeadInsertEventTap,
    kCGSessionEventTap,
)

from .app_logging import logger
from .constants import (
    ARROW_KEY_CODES,
    FN_KEY_CODE,
    KEY_NAMES,
    MOD_COMMAND,
    MOD_CONTROL,
    MOD_FN,
    MOD_OPTION,
    MOD_SHIFT,
    kCGKeyboardEventKeycode,
)


def format_keystroke(key_code, flags):
    """Build a human-readable label like '⌘⇧A' from key code + modifier flags."""
    parts = []
    if flags & MOD_CONTROL:
        parts.append("⌃")
    if flags & MOD_OPTION:
        parts.append("⌥")
    if flags & MOD_SHIFT:
        parts.append("⇧")
    if flags & MOD_COMMAND:
        parts.append("⌘")
    if flags & MOD_FN:
        parts.append("fn+")
    parts.append(KEY_NAMES.get(key_code, f"key{key_code}"))
    return "".join(parts)


class InputController:
    def trigger_mic(self, config):
        mic_cmd = config.get("mic_command", "fn")

        if mic_cmd == "fn":
            for _ in range(2):
                event_down = CGEventCreateKeyboardEvent(None, FN_KEY_CODE, True)
                CGEventPost(kCGHIDEventTap, event_down)
                event_up = CGEventCreateKeyboardEvent(None, FN_KEY_CODE, False)
                CGEventPost(kCGHIDEventTap, event_up)
                time.sleep(0.05)
            return

        if isinstance(mic_cmd, dict) and mic_cmd.get("type") == "keystroke":
            key_code = mic_cmd["key_code"]
            flags = mic_cmd.get("flags", 0)
            event_down = CGEventCreateKeyboardEvent(None, key_code, True)
            if flags:
                CGEventSetFlags(event_down, flags)
            CGEventPost(kCGHIDEventTap, event_down)
            event_up = CGEventCreateKeyboardEvent(None, key_code, False)
            if flags:
                CGEventSetFlags(event_up, flags)
            CGEventPost(kCGHIDEventTap, event_up)
            return

        if isinstance(mic_cmd, str):
            try:
                subprocess.Popen(
                    mic_cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                logger.warning("MIC command failed", exc_info=True)

    def learn_keystroke(self, config, config_store):
        captured = {}

        def callback(proxy, event_type, event, refcon):
            if event_type == kCGEventKeyDown:
                captured["key_code"] = CGEventGetIntegerValueField(
                    event, kCGKeyboardEventKeycode
                )
                captured["flags"] = CGEventGetFlags(event)
                CoreFoundation.CFRunLoopStop(CoreFoundation.CFRunLoopGetCurrent())
                return None
            if event_type == kCGEventFlagsChanged:
                flags = CGEventGetFlags(event)
                key_code = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                if flags & (MOD_SHIFT | MOD_CONTROL | MOD_OPTION | MOD_COMMAND | MOD_FN):
                    captured["key_code"] = key_code
                    captured["flags"] = flags
                    CoreFoundation.CFRunLoopStop(CoreFoundation.CFRunLoopGetCurrent())
                    return None
            return event

        event_mask = (1 << kCGEventKeyDown) | (1 << kCGEventFlagsChanged)
        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            0,
            event_mask,
            callback,
            None,
        )

        if tap is None:
            logger.error("Failed to create event tap — check Accessibility permissions")
            print("  Failed to create event tap — check Accessibility permissions")
            return

        source = CoreFoundation.CFMachPortCreateRunLoopSource(None, tap, 0)
        loop = CoreFoundation.CFRunLoopGetCurrent()
        CoreFoundation.CFRunLoopAddSource(loop, source, CoreFoundation.kCFRunLoopCommonModes)

        print("  Press the key (or combo) you want for MIC...")
        CoreFoundation.CFRunLoopRun()
        CoreFoundation.CFRunLoopRemoveSource(
            loop, source, CoreFoundation.kCFRunLoopCommonModes
        )

        if not captured:
            print("  No keystroke captured")
            return

        key_code = captured["key_code"]
        flags = captured["flags"]
        clean_flags = flags & (MOD_SHIFT | MOD_CONTROL | MOD_OPTION | MOD_COMMAND | MOD_FN)
        label = format_keystroke(key_code, clean_flags)

        config["mic_command"] = {
            "type": "keystroke",
            "key_code": key_code,
            "flags": clean_flags,
            "label": label,
        }
        config_store.save(config)
        print(f"  mic → {label}")

    def send_key(self, key_name):
        if key_name == "Return":
            script = 'tell application "System Events" to key code 36'
        elif key_name in ARROW_KEY_CODES:
            script = f'tell application "System Events" to key code {ARROW_KEY_CODES[key_name]}'
        else:
            script = f'tell application "System Events" to keystroke "{key_name}"'
        subprocess.run(["osascript", "-e", script], capture_output=True)
