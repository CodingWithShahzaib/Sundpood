from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from PyQt5 import QtWidgets

from data.app_context import ctx

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav"}
DEFAULT_SOUND_DIR = "sounds"
LEGACY_SOUND_DIR = "sound"


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


def normalize_sound_path(path: Any) -> str:
    return os.path.normpath(str(path or ""))


def resolve_sound_directory(dir_: str) -> str:
    preferred = normalize_sound_path(dir_ or DEFAULT_SOUND_DIR)
    legacy = normalize_sound_path(LEGACY_SOUND_DIR)
    if preferred.lower() != legacy.lower() and os.path.isdir(legacy) and not os.path.exists(preferred):
        try:
            os.replace(legacy, preferred)
        except OSError:
            return legacy
    return preferred


def iter_sound_paths_from_sounds(sounds: Any):
    for category in sounds or []:
        if not isinstance(category, list) or len(category) < 2:
            continue
        dir_path = normalize_sound_path(category[0])
        for sound_name in category[1:]:
            yield normalize_sound_path(os.path.join(dir_path, sound_name))


def normalize_hotkeys(hotkeys: Any, sounds: Any) -> Dict[str, str]:
    if not isinstance(hotkeys, dict):
        return {}

    valid_paths = {path.lower(): path for path in iter_sound_paths_from_sounds(sounds)}
    by_basename: Dict[str, str] = {}
    for path in valid_paths.values():
        by_basename.setdefault(os.path.basename(path).lower(), path)

    normalized: Dict[str, str] = {}
    for key, raw_path in hotkeys.items():
        path = normalize_sound_path(raw_path)
        if not path:
            continue
        lower_path = path.lower()
        if lower_path in valid_paths:
            normalized[str(key)] = valid_paths[lower_path]
            continue

        fixed = by_basename.get(os.path.basename(path).lower())
        if fixed:
            normalized[str(key)] = fixed
    return normalized


def normalize_sound_profiles(sound_profiles: Any, sounds: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(sound_profiles, dict):
        return {}

    valid_paths = {path.lower(): path for path in iter_sound_paths_from_sounds(sounds)}
    by_basename: Dict[str, str] = {}
    for path in valid_paths.values():
        by_basename.setdefault(os.path.basename(path).lower(), path)

    normalized: Dict[str, Dict[str, Any]] = {}
    for raw_path, profile in sound_profiles.items():
        if not isinstance(profile, dict):
            continue
        path = normalize_sound_path(raw_path)
        if not path:
            continue

        resolved = valid_paths.get(path.lower())
        if not resolved:
            resolved = by_basename.get(os.path.basename(path).lower())
        if not resolved:
            continue

        key = resolved.lower()
        existing = normalized.get(key, {})
        merged = dict(existing)
        merged.update(profile)
        normalized[key] = merged
    return normalized


def get_files(dir_: str, config_path: str) -> None:
    """
    Scan sound folders and ensure config file exists/contains the expected keys.
    Mirrors the original behavior from the old monolithic main.py.
    """
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Critical)
    dir_ = resolve_sound_directory(dir_)

    msg.setText(f"You don't have any sounds in '{os.path.basename(dir_)}' folder")
    msg.setInformativeText("download sound in .wav / .mp3 / .m4a format")
    msg.setWindowTitle("Error")

    existing_cfg: Dict[str, Any] = {}
    if os.path.exists(config_path):
        try:
            existing_cfg = jsonread(config_path) or {}
        except Exception:
            existing_cfg = {}

    if os.path.exists(dir_):
        if len(os.listdir(dir_)) == 0:
            msg.exec_()

        sounds = []
        sounds_list = [os.path.join(dir_, "")]

        for i in os.listdir(dir_):
            if os.path.isfile(os.path.join(dir_, i)):
                if os.path.splitext(i)[1].lower() in AUDIO_EXTENSIONS:
                    sounds_list.append(i)
            else:
                sounds_list_cat = [os.path.join(dir_, i)]
                for x in os.listdir(os.path.join(dir_, i)):
                    if os.path.isfile(os.path.join(dir_, i, x)):
                        if os.path.splitext(x)[1].lower() in AUDIO_EXTENSIONS:
                            sounds_list_cat.append(x)
                sounds.append(sounds_list_cat)
        sounds.append(sounds_list)

        # Merge-preserve config: keep unknown keys and only fill defaults.
        sounds_list_out: Dict[str, Any] = dict(existing_cfg) if isinstance(existing_cfg, dict) else {}
        sounds_list_out["sounds"] = sounds
        sounds_list_out["hotkeys"] = normalize_hotkeys(existing_cfg.get("hotkeys", {}), sounds)
        sounds_list_out.setdefault("Theme", "None")
        sounds_list_out.setdefault(
            "KEYS_CMD",
            {
                "select_move_up": " ",
                "select_move_down": " ",
                "select_move_left": " ",
                "select_move_right": " ",
                "play_sound": " ",
                "stop_sound": " ",
            },
        )
        sounds_list_out.setdefault("output_device", None)
        sounds_list_out.setdefault("input_device", None)
        sounds_list_out.setdefault("virtual_mic_device", None)
        sounds_list_out.setdefault("sound_settings", dict(ctx.sound_settings))
        sounds_list_out.setdefault("ui_settings", dict(ctx.ui_settings))
        sounds_list_out["sound_profiles"] = normalize_sound_profiles(
            existing_cfg.get("sound_profiles", {}),
            sounds,
        )

        jsonwrite(config_path, sounds_list_out)
    else:
        sounds_list_out: Dict[str, Any] = dict(existing_cfg) if isinstance(existing_cfg, dict) else {}
        sounds_list_out["hotkeys"] = normalize_hotkeys(existing_cfg.get("hotkeys", {}), [])
        sounds_list_out["sounds"] = ""
        sounds_list_out.setdefault("Theme", "None")
        sounds_list_out.setdefault(
            "KEYS_CMD",
            {
                "select_move_up": " ",
                "select_move_down": " ",
                "select_move_left": " ",
                "select_move_right": " ",
                "play_sound": " ",
                "stop_sound": " ",
            },
        )
        sounds_list_out.setdefault("output_device", None)
        sounds_list_out.setdefault("input_device", None)
        sounds_list_out.setdefault("virtual_mic_device", None)
        sounds_list_out.setdefault("sound_settings", dict(ctx.sound_settings))
        sounds_list_out.setdefault("ui_settings", dict(ctx.ui_settings))
        sounds_list_out["sound_profiles"] = normalize_sound_profiles(
            existing_cfg.get("sound_profiles", {}),
            [],
        )
        jsonwrite(config_path, sounds_list_out)
        os.mkdir(dir_)
        msg.exec_()


def save_settings_to_config() -> None:
    """
    Persist current settings/hotkeys/menu/theme/devices into the JSON config.
    This replaces the old `save()` global function.
    """
    if not getattr(ctx, "config_loaded", False):
        return

    cfg = jsonread(ctx.config_path) or {}
    sounds = cfg.get("sounds", [])

    KEYS_JSON: Dict[str, str] = {}
    for i in (ctx.KEYS_CMD or {}).keys():
        KEYS_JSON[ctx.COMMAND_DICT[i]] = ctx.KEYS_CMD[i]
    if not KEYS_JSON and isinstance(cfg.get("KEYS_CMD"), dict):
        KEYS_JSON = dict(cfg.get("KEYS_CMD"))

    try:
        theme = ctx.pref.themesList.currentItem().text()
    except Exception:
        theme = jsonread(ctx.config_path).get("Theme", "None")

    try:
        output_device = ctx.pref.output_device_combo.currentText() or cfg.get("output_device", None)
        input_device = ctx.pref.input_device_combo.currentText() or cfg.get("input_device", None)
        virtual_mic_device = ctx.pref.virtual_mic_combo.currentText() or cfg.get("virtual_mic_device", None)
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
        if hasattr(ctx.pref, "windows_mic_autoswitch_checkbox"):
            ctx.sound_settings["auto_switch_windows_mic"] = (
                ctx.pref.windows_mic_autoswitch_checkbox.isChecked()
            )
    except Exception:
        pass

    try:
        ctx.sound_settings["stop_same_hotkey"] = ctx.win.stop_same_hotkey_checkbox.isChecked()
    except Exception:
        pass

    hotkeys_source = ctx.hotkeys if ctx.hotkeys else cfg.get("hotkeys", {})
    profiles_source = ctx.sound_profiles if ctx.sound_profiles else cfg.get("sound_profiles", {})
    normalized_hotkeys = normalize_hotkeys(hotkeys_source, sounds)
    ctx.hotkeys = normalized_hotkeys
    normalized_profiles = normalize_sound_profiles(profiles_source, sounds)
    ctx.sound_profiles = normalized_profiles

    # Merge-preserve: keep unknown keys.
    out: Dict[str, Any] = dict(cfg) if isinstance(cfg, dict) else {}
    out.update(
        {
            "sounds": sounds,
            "hotkeys": normalized_hotkeys,
            "Theme": theme,
            "KEYS_CMD": KEYS_JSON,
            "output_device": output_device,
            "input_device": input_device,
            "virtual_mic_device": virtual_mic_device,
            "sound_settings": ctx.sound_settings,
            "ui_settings": ctx.ui_settings,
            "sound_profiles": normalized_profiles,
        }
    )
    jsonwrite(ctx.config_path, out)

