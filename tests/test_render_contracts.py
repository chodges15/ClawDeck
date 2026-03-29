"""Tests for rendering contracts, marquee behavior, and mode layouts."""

from unittest.mock import MagicMock, patch

from PIL import Image

from clawdeck.constants import (
    COLOR_BG_ACTIVE,
    COLOR_BG_DEFAULT,
    COLOR_BG_NAV_EMPTY,
    COLOR_BG_PERMISSION,
    COLOR_BG_WORKING,
)


def test_button_dimensions_uses_pil_helper_image_size(controller, fake_deck):
    controller.deck = fake_deck

    with patch("clawdeck.render.PILHelper.create_image", return_value=Image.new("RGB", (96, 64))) as create_mock:
        assert controller._button_dimensions() == (96, 64)

    create_mock.assert_called_once_with(fake_deck, background=COLOR_BG_DEFAULT)


def test_button_dimensions_falls_back_when_pil_helper_fails(controller, fake_deck):
    controller.deck = fake_deck

    with patch("clawdeck.render.PILHelper.create_image", side_effect=RuntimeError("boom")):
        assert controller._button_dimensions() == (72, 72)


def test_render_button_returns_native_image_and_draws_border(controller, fake_deck):
    fake_deck.button_size = (72, 72)
    controller.deck = fake_deck

    image = controller._render_button(
        "T1",
        bg=(1, 2, 3),
        fg=(255, 255, 255),
        border_color=(255, 0, 0),
        border_width=4,
    )

    assert image.size == (72, 72)
    assert image.getpixel((0, 0)) == (255, 0, 0)


def test_render_button_truncates_long_subtitle(controller, fake_deck):
    controller.deck = fake_deck
    recorder = MagicMock()
    recorder.text_calls = []

    def fake_textbbox(_xy, text, font=None):
        width = sum(4 if ch == "…" else 12 for ch in text)
        return (0, 0, width, 10)

    def fake_text(_xy, text, font=None, fill=None):
        recorder.text_calls.append(text)

    recorder.rectangle.return_value = None
    recorder.textbbox.side_effect = fake_textbbox
    recorder.text.side_effect = fake_text

    with patch("clawdeck.render.PILHelper.create_image", return_value=Image.new("RGB", (72, 72))):
        with patch("clawdeck.render.PILHelper.to_native_format", side_effect=lambda deck, image: image):
            with patch("clawdeck.render.ImageDraw.Draw", return_value=recorder):
                controller._render_button("", subtitle="this subtitle is intentionally too wide")

    assert len(recorder.text_calls) == 1
    assert recorder.text_calls[0].endswith("…")


def test_render_scroll_strip_uses_permission_palette_and_width(controller, fake_deck):
    fake_deck.button_size = (10, 10)
    controller.deck = fake_deck

    strip = controller._render_scroll_strip("Bash: npm test -- --watch=false")

    assert strip.size[1] == 10
    assert strip.size[0] > 40
    assert strip.getpixel((0, 0)) == tuple(max(c // 3, 20) for c in COLOR_BG_PERMISSION)


def test_render_scroll_button_wraps_between_strip_edges(controller, fake_deck):
    fake_deck.button_size = (4, 2)
    controller.deck = fake_deck
    strip = Image.new("RGB", (10, 2))
    colors = [
        (255, 0, 0),
        (255, 128, 0),
        (255, 255, 0),
        (0, 255, 0),
        (0, 255, 255),
        (0, 0, 255),
        (128, 0, 255),
        (255, 0, 255),
        (255, 255, 255),
        (0, 0, 0),
    ]
    for x, color in enumerate(colors):
        for y in range(2):
            strip.putpixel((x, y), color)

    image = controller._render_scroll_button(strip, offset=8, button_idx=0)

    assert [image.getpixel((x, 0)) for x in range(4)] == [colors[8], colors[9], colors[0], colors[1]]


def test_draw_row_mode_leaves_unmapped_info_buttons_dark(controller, fake_deck):
    controller.deck = fake_deck

    def fake_render(label, bg=COLOR_BG_DEFAULT, fg=None, border_color=None, border_width=8, subtitle=None):
        return {
            "label": label,
            "bg": bg,
            "subtitle": subtitle,
            "border": border_color,
        }

    controller._render_button = fake_render

    controller._draw_row_mode()

    assert fake_deck.images[0]["label"] == "T1"
    for key in (1, 2, 3, 4):
        assert fake_deck.images[key] == {
            "label": "",
            "bg": COLOR_BG_DEFAULT,
            "subtitle": None,
            "border": None,
        }


def test_draw_row_mode_permission_row_shows_static_session_info(controller, fake_deck):
    controller.deck = fake_deck
    controller.slot_tty = {0: "ttys001"}
    controller.slot_hook_cwd = {0: "/Users/tester/src/project"}
    controller.slot_branch = {0: "feature/session-info"}

    def fake_render(label, bg=COLOR_BG_DEFAULT, fg=None, border_color=None, border_width=8, subtitle=None):
        return {"label": label, "subtitle": subtitle, "bg": bg, "border": border_color}

    controller._render_button = fake_render

    controller._draw_row_mode()

    assert [fake_deck.images[key] for key in (1, 2, 3, 4)] == [
        {"label": "DIR", "subtitle": "project", "bg": COLOR_BG_DEFAULT, "border": None},
        {"label": "⎇", "subtitle": "feature/session-info", "bg": COLOR_BG_DEFAULT, "border": None},
        {"label": "DIFF", "subtitle": "review", "bg": COLOR_BG_DEFAULT, "border": None},
        {"label": "Continue", "subtitle": None, "bg": COLOR_BG_WORKING, "border": None},
    ]


def test_draw_row_mode_uses_hook_cwd_for_directory_cell(controller, fake_deck):
    controller.deck = fake_deck
    controller.slot_tty = {0: "ttys001"}
    controller.slot_cwd = {0: "/"}
    controller.slot_hook_cwd = {0: "/Users/tester/src/project"}
    controller.slot_branch = {0: "main"}

    def fake_render(label, bg=COLOR_BG_DEFAULT, fg=None, border_color=None, border_width=8, subtitle=None):
        return {"label": label, "subtitle": subtitle, "bg": bg, "border": border_color}

    controller._render_button = fake_render

    controller._draw_row_mode()

    assert fake_deck.images[1]["label"] == "DIR"
    assert fake_deck.images[1]["subtitle"] == "project"
    assert fake_deck.images[2]["label"] == "⎇"
    assert fake_deck.images[2]["subtitle"] == "main"
    assert fake_deck.images[3]["label"] == "DIFF"
    assert fake_deck.images[3]["subtitle"] == "review"
    assert fake_deck.images[4]["label"] == "Continue"
    assert fake_deck.images[4]["subtitle"] is None
    assert fake_deck.images[4]["bg"] == COLOR_BG_WORKING


def test_draw_row_mode_does_not_fallback_to_tty_shell_cwd(controller, fake_deck):
    controller.deck = fake_deck
    controller.slot_tty = {0: "ttys001"}
    controller.slot_cwd = {0: "/"}

    def fake_render(label, bg=COLOR_BG_DEFAULT, fg=None, border_color=None, border_width=8, subtitle=None):
        return {"label": label, "subtitle": subtitle, "bg": bg, "border": border_color}

    controller._render_button = fake_render

    controller._draw_row_mode()

    assert fake_deck.images[1]["label"] == "DIR"
    assert fake_deck.images[1]["subtitle"] == "Unknown"


def test_draw_row_mode_overlays_diff_feedback(controller, fake_deck):
    controller.deck = fake_deck
    controller.slot_tty = {0: "ttys001"}
    controller.info_feedback = {(0, 2): {"label": "DIFF", "subtitle": "clean", "expires_at": 99.0}}

    def fake_render(label, bg=COLOR_BG_DEFAULT, fg=None, border_color=None, border_width=8, subtitle=None):
        return {"label": label, "subtitle": subtitle, "bg": bg, "border": border_color}

    controller._render_button = fake_render

    controller._draw_row_mode()

    assert fake_deck.images[3]["label"] == "DIFF"
    assert fake_deck.images[3]["subtitle"] == "clean"


def test_draw_row_mode_working_row_shows_red_cancel_button(controller, fake_deck):
    controller.deck = fake_deck
    controller.slot_tty = {0: "ttys001"}
    controller.slot_status = {0: "working"}

    def fake_render(label, bg=COLOR_BG_DEFAULT, fg=None, border_color=None, border_width=8, subtitle=None):
        return {"label": label, "subtitle": subtitle, "bg": bg, "border": border_color}

    controller._render_button = fake_render

    controller._draw_row_mode()

    assert fake_deck.images[4]["label"] == "Cancel"
    assert fake_deck.images[4]["subtitle"] is None
    assert fake_deck.images[4]["bg"] == COLOR_BG_PERMISSION


def test_draw_nav_mode_uses_nav_styles_and_active_border(controller, fake_deck):
    controller.deck = fake_deck
    controller.active_slot = 10

    def fake_render(label, bg=COLOR_BG_DEFAULT, fg=None, border_color=None, border_width=8, subtitle=None):
        return {
            "label": label,
            "bg": bg,
            "subtitle": subtitle,
            "border": border_color,
        }

    controller._render_button = fake_render

    controller._draw_nav_mode()

    assert fake_deck.images[0]["label"] == "1"
    assert fake_deck.images[9]["label"] == "BACK"
    assert fake_deck.images[5] == {
        "label": "",
        "bg": COLOR_BG_NAV_EMPTY,
        "subtitle": None,
        "border": None,
    }
    assert fake_deck.images[10]["label"] == "MIC"
    assert fake_deck.images[10]["border"] == controller._color("active", COLOR_BG_ACTIVE)
