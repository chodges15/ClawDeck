"""Rendering helpers that turn controller state into Stream Deck images."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from StreamDeck.ImageHelpers import PILHelper

from .config import ConfigStore
from .constants import (
    COLOR_BG_ACTIVE,
    COLOR_BG_DEFAULT,
    COLOR_BG_IDLE,
    COLOR_BG_NAV_EMPTY,
    COLOR_BG_PERMISSION,
    COLOR_BG_WORKING,
    COLOR_FG_ACTIVE,
    COLOR_FG_DEFAULT,
    COLOR_FG_IDLE,
    COLOR_FG_PERMISSION,
    COLOR_FG_WORKING,
    DEFAULT_SCROLL_SPEED,
    KEYS_PER_ROW,
    NAV_BUTTON_STYLES,
    SESSIONS,
    TOTAL_KEYS,
    MODE_NAV,
)
from .layout import key_to_session, session_label_key


class DeckRenderer:
    """Render row-mode, nav-mode, and scrolling status button images."""

    def __init__(self, config_store=None):
        """Initialize the renderer and load its font set."""
        self.config_store = config_store or ConfigStore()
        self._init_fonts()

    def _init_fonts(self):
        """Load preferred fonts and fall back to Pillow defaults."""
        candidates = [
            "/System/Library/Fonts/SFCompact.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Geneva.ttf",
            "/Library/Fonts/Arial.ttf",
        ]

        def load(size):
            """Load the first available candidate font at the requested size."""
            for path in candidates:
                try:
                    return ImageFont.truetype(path, size)
                except (IOError, OSError):
                    continue
            return ImageFont.load_default()

        self.font_sm = load(12)
        self.font_md = load(18)
        self.font_lg = load(26)
        self.font_xs = load(9)

    def pick_font(self, label):
        """Choose a label font size based on label length."""
        if len(label) <= 2:
            return self.font_lg
        if len(label) <= 4:
            return self.font_md
        return self.font_sm

    def button_dimensions(self, deck):
        """Return the rendered button size for a deck."""
        if deck:
            try:
                image = PILHelper.create_image(deck, background=COLOR_BG_DEFAULT)
                return image.size
            except Exception:
                pass
        return (72, 72)

    def render_button(
        self,
        deck,
        label,
        bg=COLOR_BG_DEFAULT,
        fg=COLOR_FG_DEFAULT,
        border_color=None,
        border_width=8,
        subtitle=None,
    ):
        """Render a single labeled deck button with optional subtitle and border."""
        image = PILHelper.create_image(deck, background=bg)
        draw = ImageDraw.Draw(image)
        width, height = image.size

        if border_color:
            for index in range(border_width):
                draw.rectangle(
                    [index, index, width - 1 - index, height - 1 - index],
                    outline=border_color,
                )

        bar_h = 0
        if subtitle:
            bar_h = 16
            draw.rectangle([0, 0, width, bar_h], fill=(0, 0, 0, 153))
            display_subtitle = subtitle
            sub_bbox = draw.textbbox((0, 0), display_subtitle, font=self.font_xs)
            sub_tw = sub_bbox[2] - sub_bbox[0]
            while sub_tw > width - 10 and len(display_subtitle) > 3:
                display_subtitle = display_subtitle[:-1]
                sub_bbox = draw.textbbox((0, 0), f"{display_subtitle}…", font=self.font_xs)
                sub_tw = sub_bbox[2] - sub_bbox[0]
            if display_subtitle != subtitle:
                display_subtitle = f"{display_subtitle}…"
            sub_x = (width - sub_tw) / 2
            sub_y = (bar_h - (sub_bbox[3] - sub_bbox[1])) / 2 - 1
            draw.text(
                (sub_x, sub_y),
                display_subtitle,
                font=self.font_xs,
                fill=(255, 255, 255),
            )

        if label:
            font = self.pick_font(label)
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            x = (width - tw) / 2
            y = (height - th) / 2 - 2 + (bar_h / 2 if bar_h else 0)
            draw.text((x, y), label, font=font, fill=fg)

        return PILHelper.to_native_format(deck, image)

    def first_display_value(self, value):
        """Extract the first printable leaf value from nested tool input."""
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            for item in value:
                found = self.first_display_value(item)
                if found:
                    return found
            return None
        if isinstance(value, dict):
            for item in value.values():
                found = self.first_display_value(item)
                if found:
                    return found
            return None
        return str(value)

    def format_tool_command(self, tool_info):
        """Build a short permission-prompt summary from tool metadata."""
        if not tool_info:
            return "Permission required"

        tool_name = str(tool_info.get("tool_name") or "Tool")
        tool_input = tool_info.get("tool_input")
        lower_name = tool_name.lower()

        summary = None
        if isinstance(tool_input, dict):
            if lower_name == "bash":
                summary = tool_input.get("command") or tool_input.get("cmd")
            elif lower_name in {"read", "edit", "write", "multiedit"}:
                summary = (
                    tool_input.get("file_path")
                    or tool_input.get("path")
                    or self.first_display_value(tool_input.get("paths"))
                )

        if summary is None:
            summary = self.first_display_value(tool_input)

        if summary:
            return f"{tool_name}: {summary}"
        return tool_name

    def format_cwd(self, config, path):
        """Format a working-directory path for button subtitle display."""
        if not path:
            return None

        mode = config.get("folder_label", "last")
        if mode == "off":
            return None

        home = str(Path.home())
        tilde_path = "~" + path[len(home):] if path.startswith(home) else path

        if mode == "full":
            return tilde_path
        if mode == "two":
            parts = Path(path).parts
            return "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]
        return Path(path).name

    def render_scroll_strip(self, deck, config, text):
        """Render the repeating strip used for permission scrolling text."""
        button_w, button_h = self.button_dimensions(deck)
        viewport_w = button_w * (KEYS_PER_ROW - 1)
        gap = max(button_w // 2, 24)
        background = tuple(
            max(channel // 3, 20)
            for channel in self.config_store.color(config, "permission", COLOR_BG_PERMISSION)
        )

        probe = Image.new("RGB", (1, 1), background)
        draw = ImageDraw.Draw(probe)
        bbox = draw.textbbox((0, 0), text, font=self.font_sm)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        strip_w = max(text_w + gap * 2, viewport_w + gap)
        strip = Image.new("RGB", (strip_w, button_h), background)
        draw = ImageDraw.Draw(strip)
        text_x = gap
        text_y = (button_h - text_h) / 2 - bbox[1]
        draw.text((text_x, text_y), text, font=self.font_sm, fill=COLOR_FG_PERMISSION)
        return strip

    def ensure_scroll_strip(self, deck, state, config, label_key):
        """Cache and return the scrolling strip for a permission row."""
        text = self.format_tool_command(state.slot_tool_info.get(label_key))
        if label_key not in state.scroll_images or state.scroll_text.get(label_key) != text:
            state.scroll_images[label_key] = self.render_scroll_strip(deck, config, text)
            state.scroll_text[label_key] = text
            state.scroll_offsets[label_key] = 0
        return state.scroll_images[label_key]

    def render_scroll_button(self, deck, strip, offset, button_idx):
        """Crop one visible button-sized slice from a scrolling strip."""
        button_w, button_h = self.button_dimensions(deck)
        start = (offset + button_idx * button_w) % strip.width

        if start + button_w <= strip.width:
            crop = strip.crop((start, 0, start + button_w, button_h))
        else:
            right = strip.crop((start, 0, strip.width, button_h))
            left = strip.crop((0, 0, button_w - right.width, button_h))
            crop = Image.new("RGB", (button_w, button_h))
            crop.paste(right, (0, 0))
            crop.paste(left, (right.width, 0))

        return PILHelper.to_native_format(deck, crop)

    def advance_scroll_offset(self, state, config, label_key, strip_width):
        """Advance one permission-row marquee offset based on scroll speed."""
        speed = max(int(config.get("scroll_speed", DEFAULT_SCROLL_SPEED)), 0)
        if strip_width <= 0:
            state.scroll_offsets[label_key] = 0
            return 0
        next_offset = (state.scroll_offsets.get(label_key, 0) + speed) % strip_width
        state.scroll_offsets[label_key] = next_offset
        return next_offset

    def advance_scroll_offsets(self, deck, state, config):
        """Advance marquee offsets for every permission row."""
        changed = False
        for label_key, status in state.slot_status.items():
            if status != "permission":
                continue
            strip = self.ensure_scroll_strip(deck, state, config, label_key)
            old_offset = state.scroll_offsets.get(label_key, 0)
            new_offset = self.advance_scroll_offset(state, config, label_key, strip.width)
            if new_offset != old_offset:
                changed = True
        return changed

    def get_slot_style(self, config, state, slot):
        """Resolve the label-button palette for a session slot."""
        if isinstance(slot, str):
            label_key = session_label_key(slot)
        else:
            session = key_to_session(slot)
            label_key = session_label_key(session) if session else slot

        is_active = label_key == state.active_slot
        status = state.slot_status.get(label_key)
        active_color = self.config_store.color(config, "active", COLOR_BG_ACTIVE)
        border = active_color if is_active else None

        if status == "idle":
            return self.config_store.color(config, "idle", COLOR_BG_IDLE), COLOR_FG_IDLE, border
        if status == "working":
            return (
                self.config_store.color(config, "working", COLOR_BG_WORKING),
                COLOR_FG_WORKING,
                border,
            )
        if status == "permission":
            perm_color = self.config_store.color(config, "permission", COLOR_BG_PERMISSION)
            if state.blink_on:
                return perm_color, COLOR_FG_PERMISSION, border
            dim = tuple(max(channel // 4, 10) for channel in perm_color)
            return dim, (100, 100, 100), border

        if is_active:
            return active_color, self.config_store.color(config, "label_text", COLOR_FG_ACTIVE), None
        return COLOR_BG_DEFAULT, COLOR_FG_DEFAULT, None

    def draw_row_mode(self, deck, state, config):
        """Render the full deck in row mode."""
        for session in SESSIONS:
            label_key = session_label_key(session)
            bg, fg, border = self.get_slot_style(config, state, label_key)
            deck.set_key_image(
                label_key,
                self.render_button(deck, session, bg, fg, border_color=border),
            )

            info_keys = range(label_key + 1, label_key + KEYS_PER_ROW)
            status = state.slot_status.get(label_key)
            is_mapped = label_key in state.slot_tty

            if not is_mapped:
                for key in info_keys:
                    deck.set_key_image(
                        key, self.render_button(deck, "", COLOR_BG_DEFAULT, COLOR_FG_DEFAULT)
                    )
                continue

            if status == "permission":
                strip = self.ensure_scroll_strip(deck, state, config, label_key)
                offset = state.scroll_offsets.get(label_key, 0)
                for button_idx, key in enumerate(info_keys):
                    deck.set_key_image(
                        key, self.render_scroll_button(deck, strip, offset, button_idx)
                    )
                continue

            subtitle = None
            raw_cwd = state.slot_cwd.get(label_key)
            if raw_cwd and config.get("button_labels", True):
                subtitle = self.format_cwd(config, raw_cwd)

            first_key = label_key + 1
            deck.set_key_image(
                first_key,
                self.render_button(
                    deck, "", COLOR_BG_DEFAULT, COLOR_FG_DEFAULT, subtitle=subtitle
                ),
            )
            for key in range(first_key + 1, label_key + KEYS_PER_ROW):
                deck.set_key_image(
                    key, self.render_button(deck, "", COLOR_BG_DEFAULT, COLOR_FG_DEFAULT)
                )

    def get_nav_style(self, config, key):
        """Resolve nav-button styling with user color overrides applied."""
        style = NAV_BUTTON_STYLES.get(key)
        if style is None:
            return None

        bg = style["bg"]
        if key in (0, 1, 2, 3, 4):
            bg = self.config_store.color(config, f"num_{key + 1}", bg)
        elif key in (7, 11, 12, 13):
            bg = self.config_store.color(config, "arrows", bg)
        elif key in (10, 14):
            bg = self.config_store.color(config, "mic_enter", bg)

        return {"label": style["label"], "bg": bg, "fg": style["fg"]}

    def draw_nav_mode(self, deck, state, config):
        """Render the full deck in navigation mode."""
        for key in range(TOTAL_KEYS):
            border = (
                self.config_store.color(config, "active", COLOR_BG_ACTIVE)
                if key == state.active_slot
                else None
            )
            style = self.get_nav_style(config, key)
            if style:
                deck.set_key_image(
                    key,
                    self.render_button(
                        deck,
                        style["label"],
                        style["bg"],
                        style["fg"],
                        border_color=border,
                    ),
                )
            else:
                deck.set_key_image(
                    key,
                    self.render_button(deck, "", COLOR_BG_NAV_EMPTY, border_color=border),
                )

    def update_all_buttons(self, deck, state, config):
        """Render the deck in whichever mode is currently active."""
        if state.mode == MODE_NAV:
            self.draw_nav_mode(deck, state, config)
        else:
            self.draw_row_mode(deck, state, config)
