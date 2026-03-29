from clawdeck.constants import (
    COLOR_BG_DEFAULT,
    COLOR_BG_IDLE,
    COLOR_BG_PERMISSION,
    COLOR_BG_WORKING,
    COLOR_FG_DEFAULT,
)


def test_idle_style(controller):
    controller.slot_status = {0: "idle"}
    controller.active_slot = None
    bg, fg, border = controller._get_slot_style(0)
    assert bg == COLOR_BG_IDLE
    assert border is None


def test_working_style(controller):
    controller.slot_status = {0: "working"}
    controller.active_slot = None
    bg, fg, border = controller._get_slot_style(0)
    assert bg == COLOR_BG_WORKING


def test_permission_blink_on(controller):
    controller.slot_status = {0: "permission"}
    controller.active_slot = None
    controller.blink_on = True
    bg, fg, border = controller._get_slot_style(0)
    assert bg == COLOR_BG_PERMISSION


def test_permission_blink_off(controller):
    controller.slot_status = {0: "permission"}
    controller.active_slot = None
    controller.blink_on = False
    bg, fg, border = controller._get_slot_style(0)
    assert bg != COLOR_BG_PERMISSION
    assert isinstance(bg, tuple)
    assert len(bg) == 3


def test_active_slot_gets_border(controller):
    controller.slot_status = {0: "idle"}
    controller.active_slot = 0
    bg, fg, border = controller._get_slot_style(0)
    assert border is not None


def test_inactive_slot_no_border(controller):
    controller.slot_status = {0: "idle"}
    controller.active_slot = 5
    bg, fg, border = controller._get_slot_style(0)
    assert border is None


def test_no_status_active(controller):
    controller.slot_status = {}
    controller.active_slot = 0
    bg, fg, border = controller._get_slot_style(0)
    assert isinstance(bg, tuple)
    assert len(bg) == 3
    assert border is None


def test_no_status_inactive(controller):
    controller.slot_status = {}
    controller.active_slot = None
    bg, fg, border = controller._get_slot_style(0)
    assert bg == COLOR_BG_DEFAULT
    assert fg == COLOR_FG_DEFAULT


def test_info_key_resolves_to_same_label_style(controller):
    controller.slot_status = {0: "idle"}
    bg, fg, border = controller._get_slot_style(1)
    assert bg == COLOR_BG_IDLE


def test_session_name_resolves_to_label_style(controller):
    controller.slot_status = {0: "idle"}
    bg, fg, border = controller._get_slot_style("T1")
    assert bg == COLOR_BG_IDLE


def test_nav_style_number_keys(controller):
    for key, expected_label in enumerate(["1", "2", "3", "4", "5"]):
        result = controller._get_nav_style(key)
        assert result is not None
        assert expected_label in str(result["label"])


def test_nav_style_arrows(controller):
    for key in [7, 11, 12, 13]:
        result = controller._get_nav_style(key)
        assert result is not None


def test_nav_style_invalid_key(controller):
    assert controller._get_nav_style(15) is None
