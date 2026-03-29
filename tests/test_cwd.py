"""Tests for working-directory subtitle formatting modes."""

from pathlib import Path


def test_format_last_folder(controller):
    controller.config["folder_label"] = "last"
    assert controller._format_cwd("/Users/cory/Desktop/ClawDeck") == "ClawDeck"


def test_format_two_segments(controller):
    controller.config["folder_label"] = "two"
    assert controller._format_cwd("/Users/cory/Desktop/ClawDeck") == "Desktop/ClawDeck"


def test_format_full_path(controller):
    controller.config["folder_label"] = "full"
    home = str(__import__("pathlib").Path.home())
    test_path = home + "/Desktop/ClawDeck"
    assert controller._format_cwd(test_path) == "~/Desktop/ClawDeck"


def test_format_off(controller):
    controller.config["folder_label"] = "off"
    assert controller._format_cwd("/Users/cory/Desktop/ClawDeck") is None


def test_format_none_input(controller):
    controller.config["folder_label"] = "last"
    assert controller._format_cwd(None) is None


def test_format_empty_string(controller):
    controller.config["folder_label"] = "last"
    assert controller._format_cwd("") is None


def test_format_root_path(controller):
    controller.config["folder_label"] = "last"
    assert controller._format_cwd("/") == ""


def test_format_home_dir(controller):
    controller.config["folder_label"] = "full"
    home = str(Path.home())
    assert controller._format_cwd(home) == "~"


def test_format_path_with_spaces(controller):
    controller.config["folder_label"] = "last"
    assert controller._format_cwd("/Users/cory/Desktop/my project") == "my project"


def test_format_two_short_path(controller):
    controller.config["folder_label"] = "two"
    assert controller._format_cwd("/Users") == "//Users"
