from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from PyQt5 import QtWidgets

from data.app_context import ctx


def jsonread(file: str) -> Any:
    """Read JSON from file (UTF-8)."""
    with open(file, "r", encoding="utf-8") as read_file:
        return json.load(read_file)


def jsonwrite(file: str, data: Any) -> None:
    """Write JSON to file (UTF-8)."""
    with open(file, "w", encoding="utf-8") as write_file:
        write_file.write(json.dumps(data))


def find_key(d: Dict[Any, Any], val: Any) -> Optional[Any]:
    """Return first key in dict `d` with value `val`, else None."""
    return next((key for key, value in d.items() if value == val), None)


def get_files(dir_: str, config_path: str) -> None:
    """
    Scan sound folders and ensure config file exists/contains the expected keys.
    Mirrors the original behavior from the old monolithic main.py.
    """
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Critical)
    msg.setText("You don't have any sounds in 'sound' folder")
    msg.setInformativeText("download sound in .wav / .mp3 / .m4a format")
    msg.setWindowTitle("Error")

    if os.path.exists(dir_):
        if len(os.listdir(dir_)) == 0:
            msg.exec_()

        sounds = []
        sounds_list = [f"{dir_}\\"]

        for i in os.listdir(dir_):
            if os.path.isfile(os.path.join(dir_, i)):
                name = os.path.join(dir_, i)
                if name is None:
                    sounds_list.append(i)
                elif os.path.splitext(i)[1] in [".mp3", ".m4a", ".wav"]:
                    sounds_list.append(i)
            else:
                sounds_list_cat = [os.path.join(dir_, i)]
                for x in os.listdir(os.path.join(dir_, i)):
                    if os.path.isfile(os.path.join(dir_, i, x)):
                        if os.path.splitext(x)[1] in [".mp3", ".m4a", ".wav"]:
                            sounds_list_cat.append(x)
                sounds.append(sounds_list_cat)
        sounds.append(sounds_list)

        if os.path.exists(config_path):
            config_data = jsonread(config_path)
            hotkeys = config_data.get("hotkeys", {})
            theme = config_data.get("Theme", "None")
            KEYS_CMD = config_data.get("KEYS_CMD", {})
            output_device = config_data.get("output_device", None)
            input_device = config_data.get("input_device", None)
            virtual_mic_device = config_data.get("virtual_mic_device", None)
            saved_sound_settings = config_data.get("sound_settings", {})
            sounds_list_out = {
                "hotkeys": hotkeys,
                "sounds": sounds,
                "Theme": theme,
                "KEYS_CMD": KEYS_CMD,
                "output_device": output_device,
                "input_device": input_device,
                "virtual_mic_device": virtual_mic_device,
                "sound_settings": saved_sound_settings,
            }
        else:
            sounds_list_out = {
                "hotkeys": {},
                "sounds": sounds,
                "Theme": "None",
                "KEYS_CMD": {
                    "select_move_up": " ",
                    "select_move_down": " ",
                    "select_move_left": " ",
                    "select_move_right": " ",
                    "play_sound": " ",
                    "stop_sound": " ",
                },
                "output_device": None,
                "input_device": None,
                "virtual_mic_device": None,
                "sound_settings": ctx.sound_settings,
            }

        jsonwrite(config_path, sounds_list_out)
    else:
        sounds_list_out = {
            "hotkeys": {},
            "sounds": "",
            "Theme": "None",
            "KEYS_CMD": {
                "select_move_up": " ",
                "select_move_down": " ",
                "select_move_left": " ",
                "select_move_right": " ",
                "play_sound": " ",
                "stop_sound": " ",
            },
            "output_device": None,
            "input_device": None,
            "virtual_mic_device": None,
            "sound_settings": ctx.sound_settings,
        }
        jsonwrite(config_path, sounds_list_out)
        os.mkdir(dir_)
        msg.exec_()


def save_settings_to_config() -> None:
    """
    Persist current settings/hotkeys/menu/theme/devices into the JSON config.
    This replaces the old `save()` global function.
    """
    sounds = jsonread(ctx.config_path)["sounds"]

    KEYS_JSON: Dict[str, str] = {}
    for i in ctx.KEYS_CMD.keys():
        KEYS_JSON.setdefault(ctx.COMMAND_DICT[i], ctx.KEYS_CMD[i])

    try:
        theme = ctx.pref.themesList.currentItem().text()
    except Exception:
        theme = jsonread(ctx.config_path).get("Theme", "None")

    try:
        output_device = ctx.pref.output_device_combo.currentText()
        input_device = ctx.pref.input_device_combo.currentText()
        virtual_mic_device = ctx.pref.virtual_mic_combo.currentText()
    except Exception:
        cfg = jsonread(ctx.config_path)
        output_device = cfg.get("output_device", None)
        input_device = cfg.get("input_device", None)
        virtual_mic_device = cfg.get("virtual_mic_device", None)

    try:
        ctx.sound_settings["allow_overlap"] = ctx.pref.allow_overlap_checkbox.isChecked()
        ctx.sound_settings["loop_sounds"] = ctx.pref.loop_sounds_checkbox.isChecked()
        ctx.sound_settings["virtual_mic_enabled"] = ctx.pref.virtual_mic_checkbox.isChecked()
        ctx.sound_settings["mic_passthrough_enabled"] = ctx.pref.passthrough_mic_checkbox.isChecked()
    except Exception:
        pass

    try:
        ctx.sound_settings["stop_same_hotkey"] = ctx.win.stop_same_hotkey_checkbox.isChecked()
    except Exception:
        pass

    out = {
        "sounds": sounds,
        "hotkeys": ctx.hotkeys,
        "Theme": theme,
        "KEYS_CMD": KEYS_JSON,
        "output_device": output_device,
        "input_device": input_device,
        "virtual_mic_device": virtual_mic_device,
        "sound_settings": ctx.sound_settings,
    }
    jsonwrite(ctx.config_path, out)

