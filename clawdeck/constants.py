"""Shared constants for deck layout, colors, timing, and key mappings."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ITERM_APP_NAME = "iTerm2"
COLS = 5
ROWS = 3
NUM_SESSIONS = 3
SESSIONS = ["T1", "T2", "T3"]
KEYS_PER_ROW = COLS
TOTAL_KEYS = COLS * ROWS
HOLD_THRESHOLD_SEC = 0.5
FN_KEY_CODE = 63
POLL_INTERVAL = 0.2
STATUS_DIR = "/tmp/deck-status"
STATUS_STALE_SEC = 3600
PENDING_INFER_SEC = 2.0
BLINK_INTERVAL = 0.5
TTY_MAP_REFRESH_SEC = 30
ACTIVE_CWD_REFRESH_SEC = 1
BRIGHTNESS = 80
DEFAULT_SCROLL_SPEED = 2
SETTINGS_PORT_START = 19830
SETTINGS_PORT_END = 19850

# Colors (R, G, B)
COLOR_BG_DEFAULT = (0, 0, 0)
COLOR_FG_DEFAULT = (255, 255, 255)
COLOR_BG_ACTIVE = (255, 176, 0)
COLOR_FG_ACTIVE = (0, 0, 0)
COLOR_BG_IDLE = (30, 100, 220)
COLOR_FG_IDLE = (255, 255, 255)
COLOR_BG_WORKING = (30, 160, 70)
COLOR_FG_WORKING = (255, 255, 255)
COLOR_BG_PERMISSION = (200, 50, 50)
COLOR_FG_PERMISSION = (255, 255, 255)
COLOR_BG_NAV_BACK = (160, 30, 30)
COLOR_BG_NAV_ARROW = (30, 35, 55)
COLOR_FG_NAV_ARROW = (180, 200, 255)
COLOR_BG_NAV_ACTION = (230, 230, 230)
COLOR_FG_NAV_ACTION = (0, 0, 0)
COLOR_BG_NAV_EMPTY = (15, 15, 15)
COLOR_BG_NUM_1 = (180, 40, 40)
COLOR_BG_NUM_2 = (200, 120, 20)
COLOR_BG_NUM_3 = (190, 175, 20)
COLOR_BG_NUM_4 = (40, 150, 60)
COLOR_BG_NUM_5 = (40, 80, 200)

MODE_ROW = "row"
MODE_GRID = MODE_ROW  # Backward-compatible alias for older callers/tests.
MODE_NAV = "nav"

NAV_KEYMAP = {
    0: ("num", "1"),
    1: ("num", "2"),
    2: ("num", "3"),
    3: ("num", "4"),
    4: ("num", "5"),
    7: ("arrow", "Up"),
    9: ("back", None),
    10: ("whisprflow", None),
    11: ("arrow", "Left"),
    12: ("arrow", "Down"),
    13: ("arrow", "Right"),
    14: ("enter", None),
}

NAV_BUTTON_STYLES = {
    0: {"label": "1", "bg": COLOR_BG_NUM_1, "fg": COLOR_FG_DEFAULT},
    1: {"label": "2", "bg": COLOR_BG_NUM_2, "fg": COLOR_FG_DEFAULT},
    2: {"label": "3", "bg": COLOR_BG_NUM_3, "fg": COLOR_FG_DEFAULT},
    3: {"label": "4", "bg": COLOR_BG_NUM_4, "fg": COLOR_FG_DEFAULT},
    4: {"label": "5", "bg": COLOR_BG_NUM_5, "fg": COLOR_FG_DEFAULT},
    7: {"label": "↑", "bg": COLOR_BG_NAV_ARROW, "fg": COLOR_FG_NAV_ARROW},
    9: {"label": "BACK", "bg": COLOR_BG_NAV_BACK, "fg": COLOR_FG_DEFAULT},
    10: {"label": "MIC", "bg": COLOR_BG_NAV_ACTION, "fg": COLOR_FG_NAV_ACTION},
    11: {"label": "←", "bg": COLOR_BG_NAV_ARROW, "fg": COLOR_FG_NAV_ARROW},
    12: {"label": "↓", "bg": COLOR_BG_NAV_ARROW, "fg": COLOR_FG_NAV_ARROW},
    13: {"label": "→", "bg": COLOR_BG_NAV_ARROW, "fg": COLOR_FG_NAV_ARROW},
    14: {"label": "⏎", "bg": COLOR_BG_NAV_ACTION, "fg": COLOR_FG_NAV_ACTION},
}

ARROW_KEY_CODES = {"Up": 126, "Down": 125, "Left": 123, "Right": 124}

kCGKeyboardEventKeycode = 9
MOD_SHIFT = 0x20000
MOD_CONTROL = 0x40000
MOD_OPTION = 0x80000
MOD_COMMAND = 0x100000
MOD_FN = 0x800000

KEY_NAMES = {
    0: "A",
    1: "S",
    2: "D",
    3: "F",
    4: "H",
    5: "G",
    6: "Z",
    7: "X",
    8: "C",
    9: "V",
    11: "B",
    12: "Q",
    13: "W",
    14: "E",
    15: "R",
    16: "Y",
    17: "T",
    18: "1",
    19: "2",
    20: "3",
    21: "4",
    22: "6",
    23: "5",
    24: "=",
    25: "9",
    26: "7",
    27: "-",
    28: "8",
    29: "0",
    31: "O",
    32: "U",
    34: "I",
    35: "P",
    37: "L",
    38: "J",
    40: "K",
    45: "N",
    46: "M",
    36: "Return",
    48: "Tab",
    49: "Space",
    51: "Delete",
    53: "Escape",
    63: "fn",
    122: "F1",
    120: "F2",
    99: "F3",
    118: "F4",
    96: "F5",
    97: "F6",
    98: "F7",
    100: "F8",
    101: "F9",
    109: "F10",
    103: "F11",
    111: "F12",
    123: "Left",
    124: "Right",
    125: "Down",
    126: "Up",
}
