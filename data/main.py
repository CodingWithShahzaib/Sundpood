"""
SundPood entrypoint (refactored).

`launcher.py` executes this file with `exec()`, so startup logic stays here,
but implementation lives in smaller modules under `data/`.
"""

from __future__ import annotations

import os
import sys

import pygame as pg
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication

from data import keys
from data.app_context import ctx
from data.app_wiring import wire_app
from data.config_io import get_files, jsonread, normalize_hotkeys, resolve_sound_directory
from data.device_utils import find_device, init_mixer, populate_devices
from data.mic_passthrough import start_mic_passthrough
from data.playback import stop_all_sounds
from data.theme_utils import toggle_stylesheet
from data.ui_actions import refresh_hotkey_list, select_move
from data.ui_windows import HotkeysUi, MainUi, OverlayUi, PreferencesUi
from data.library_utils import category_display_name


def _register_qt_metatypes() -> None:
    """Register Qt metatypes to reduce cross-thread signal issues."""
    try:
        from PyQt5.QtCore import QItemSelection

        QtCore.qRegisterMetaType(QItemSelection)
    except Exception:
        try:
            QtCore.qRegisterMetaType("QItemSelection")
        except Exception:
            pass


def _load_config_into_ctx() -> dict:
    ctx.VERSION = 102
    ctx.dir_ = resolve_sound_directory("sounds")
    ctx.config_path = "settings.json"

    get_files(ctx.dir_, ctx.config_path)
    cfg = jsonread(ctx.config_path) or {}

    ctx.hotkeys = normalize_hotkeys(cfg.get("hotkeys", {}), cfg.get("sounds", []))
    ctx.theme = cfg.get("Theme", "None")
    ctx.menu = cfg.get("sounds", [])
    ctx.select = [0, 0]

    try:
        ctx.sound_settings.update(cfg.get("sound_settings", {}) or {})
    except Exception:
        pass

    try:
        ctx.ui_settings.update(cfg.get("ui_settings", {}) or {})
    except Exception:
        pass

    ctx.sound_profiles = cfg.get("sound_profiles", {}) or {}
    ctx.config_loaded = True
    return cfg


def _init_audio() -> None:
    pg.mixer.pre_init(44100, -16, 2, 2048)
    try:
        init_mixer(find_device())
        pg.mixer.music.set_volume(0.7)
    except Exception as e:
        print(f"Warning: Failed to initialize audio device: {e}")


def _init_ui() -> None:
    ctx.app = QApplication([])
    ctx.over = OverlayUi()
    ctx.pref = PreferencesUi()
    ctx.hotk = HotkeysUi()
    ctx.win = MainUi()

    ctx.PREF_BTN = [
        ctx.pref.select_move_up,
        ctx.pref.select_move_down,
        ctx.pref.select_move_left,
        ctx.pref.select_move_right,
        ctx.pref.play_sound,
        ctx.pref.stop_sound,
    ]


def _apply_theme_and_devices() -> None:
    if ctx.theme != "None":
        toggle_stylesheet(ctx.theme)
    try:
        ctx.pref.themesList.addItems(os.listdir("themes"))
    except Exception:
        pass
    populate_devices()


def _apply_saved_checkbox_state() -> None:
    ctx.pref.allow_overlap_checkbox.setChecked(ctx.sound_settings.get("allow_overlap", True))
    ctx.pref.loop_sounds_checkbox.setChecked(ctx.sound_settings.get("loop_sounds", False))
    ctx.pref.virtual_mic_checkbox.setChecked(ctx.sound_settings.get("virtual_mic_enabled", False))
    ctx.pref.passthrough_mic_checkbox.setChecked(ctx.sound_settings.get("mic_passthrough_enabled", False))
    ctx.win.stop_same_hotkey_checkbox.setChecked(ctx.sound_settings.get("stop_same_hotkey", False))


def _populate_lists(cfg: dict) -> None:
    for cat in cfg.get("sounds", []):
        try:
            ctx.win.catList.addItem(category_display_name(cat[0]))
        except Exception:
            pass
    refresh_hotkey_list()


def _build_command_maps() -> None:
    """
    COMMAND_DICT: lambda -> command name
    KEYS_CMD:     lambda -> key string
    """
    from data.playback import play_sound

    def _play_selected():
        try:
            play_sound(os.path.join(ctx.menu[ctx.select[0]][0], ctx.menu[ctx.select[0]][ctx.select[1]]))
        except Exception:
            pass

    ctx.COMMAND_DICT = {
        (lambda: select_move((0, -1))): "select_move_up",
        (lambda: select_move((0, 1))): "select_move_down",
        (lambda: select_move((-1, 0))): "select_move_left",
        (lambda: select_move((1, 0))): "select_move_right",
        _play_selected: "play_sound",
        (lambda: stop_all_sounds()): "stop_sound",
    }

    cfg = jsonread(ctx.config_path) or {}
    KEYS_JSON = cfg.get("KEYS_CMD", {})
    ctx.KEYS_CMD = ctx.COMMAND_DICT.copy()
    for fn in list(ctx.KEYS_CMD.keys()):
        ctx.KEYS_CMD[fn] = KEYS_JSON.get(ctx.COMMAND_DICT[fn], " ")

    for idx, key_str in enumerate(list(ctx.KEYS_CMD.values())):
        try:
            ctx.PREF_BTN[idx].setText(keys.dict_.get(key_str, key_str))
        except Exception:
            pass


if __name__ == "__main__":
    _register_qt_metatypes()
    _init_ui()
    _init_audio()

    cfg = _load_config_into_ctx()

    # Overlay upgrade (searchable overlay)
    try:
        if ctx.ui_settings.get("enhanced_overlay", True):
            ctx.over.enable_enhanced_overlay()
    except Exception:
        pass

    _apply_theme_and_devices()
    _apply_saved_checkbox_state()

    if ctx.sound_settings.get("mic_passthrough_enabled", False):
        start_mic_passthrough()

    _populate_lists(cfg)
    _build_command_maps()

    wire_app()
    try:
        from data.windows_audio import install_quit_restore_hook, sync_windows_recording_defaults

        install_quit_restore_hook()
        sync_windows_recording_defaults(notify_user=False)
    except Exception as exc:
        print(f"Windows mic auto-switch unavailable: {exc}")

    # System tray
    try:
        if ctx.ui_settings.get("tray_enabled", True):
            from data.tray import TrayController

            ctx.tray = TrayController(parent=ctx.win)
    except Exception:
        pass

    ctx.win.showMaximized()
    sys.exit(ctx.app.exec())

