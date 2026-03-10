from __future__ import annotations

import logging
import os
from time import time

from PyQt5 import QtCore, QtWidgets

from data.app_context import ctx
from data.config_io import save_settings_to_config
from data.playback import is_playback_active, play_sound, stop_all_sounds

logger = logging.getLogger("sundpood.hotkeys")

pressed_keys: set[str] = set()
push_to_talk_enabled: dict[str, bool] = {}

hotkey_last_press: dict[str, float] = {}
hotkey_last_stop: dict[str, float] = {}
HOTKEY_DEBOUNCE_TIME = 0.15
HOTKEY_STOP_DEBOUNCE_TIME = 0.3


# ---------------------------------------------------------------------------
# Signal bridge: pynput fires callbacks on a background thread.  We must
# never call pygame, numpy, or Qt widget methods from that thread – doing so
# causes silent segfaults (the "app just closes" symptom).  Instead, pynput
# callbacks only emit Qt signals which are delivered to the main thread via
# QueuedConnection.
# ---------------------------------------------------------------------------

class _HotkeyBridge(QtCore.QObject):
    sig_key_down = QtCore.pyqtSignal(str)
    sig_key_up = QtCore.pyqtSignal(str)

    @QtCore.pyqtSlot(str)
    def handle_key_down(self, key: str) -> None:
        _on_key_down(key)

    @QtCore.pyqtSlot(str)
    def handle_key_up(self, key: str) -> None:
        _on_key_up(key)


_bridge: _HotkeyBridge | None = None


def init_hotkey_bridge() -> None:
    """Must be called once from the main thread before the pynput Listener starts."""
    global _bridge
    if _bridge is not None:
        return
    _bridge = _HotkeyBridge()
    app = QtWidgets.QApplication.instance()
    if app is not None:
        _bridge.moveToThread(app.thread())
    _bridge.sig_key_down.connect(_bridge.handle_key_down, QtCore.Qt.QueuedConnection)
    _bridge.sig_key_up.connect(_bridge.handle_key_up, QtCore.Qt.QueuedConnection)


# -- public API (called by pynput Listener on its background thread) --------

def key_press_handler(key) -> None:
    key_str = str(key).replace("'", "")
    if _bridge is not None:
        _bridge.sig_key_down.emit(key_str)


def key_check(key) -> None:
    key_str = str(key).replace("'", "")
    if _bridge is not None:
        _bridge.sig_key_up.emit(key_str)


# -- slots (always execute on the Qt main thread) --------------------------

def _on_key_down(key: str) -> None:
    if key in ctx.hotkeys and push_to_talk_enabled.get(key, False):
        if key not in pressed_keys:
            pressed_keys.add(key)
            play_sound(ctx.hotkeys[key], loop=True, stop_others=False)


def _on_key_up(key: str) -> None:
    if key in pressed_keys:
        pressed_keys.discard(key)
        try:
            stop_all_sounds()
        except Exception as e:
            logger.warning("Error stopping sounds on push-to-talk release: %s", e)
        return

    if key in ctx.hotkeys:
        _handle_sound_hotkey(key)
    elif key in (ctx.KEYS_CMD or {}).values():
        _handle_command_hotkey(key)


def _handle_sound_hotkey(key: str) -> None:
    current_time = time()
    sound_path = os.path.normpath(ctx.hotkeys[key])
    logger.info("Hotkey pressed: %s -> %s", key, sound_path)

    if ctx.sound_settings.get("stop_same_hotkey", False):
        if _try_stop_same(key, sound_path, current_time):
            return

    if current_time - hotkey_last_press.get(key, 0) < HOTKEY_DEBOUNCE_TIME:
        return

    hotkey_last_press[key] = current_time

    overlap_allowed = ctx.sound_settings.get("allow_overlap", True)
    loop_enabled = ctx.sound_settings.get("loop_sounds", False)

    sound_path = _resolve_missing(key, sound_path)
    if sound_path is None:
        return

    try:
        logger.info("Playing hotkey sound: %s", sound_path)
        ctx.current_playing_hotkey = key
        result = play_sound(sound_path, loop=loop_enabled, stop_others=not overlap_allowed)
        if result:
            # play_sound() may call stop_all_sounds(), which clears these fields.
            # Restore the identity of the sound that this hotkey started.
            ctx.current_playing_hotkey = key
            ctx.current_playing_sound = os.path.normpath(sound_path)
        else:
            ctx.current_playing_hotkey = None
            ctx.current_playing_sound = None
    except Exception as e:
        logger.warning("Error playing sound from hotkey '%s': %s", key, e)
        ctx.current_playing_hotkey = None
        ctx.current_playing_sound = None


def _try_stop_same(key: str, sound_path: str, current_time: float) -> bool:
    if current_time - hotkey_last_stop.get(key, 0) < HOTKEY_STOP_DEBOUNCE_TIME:
        return True

    try:
        norm = os.path.normpath(os.path.abspath(sound_path)).lower()
    except Exception:
        norm = os.path.normpath(sound_path).lower()

    is_same_hotkey = ctx.current_playing_hotkey == key
    is_same_sound = False
    if ctx.current_playing_sound:
        try:
            cur_norm = os.path.normpath(os.path.abspath(ctx.current_playing_sound)).lower()
        except Exception:
            cur_norm = os.path.normpath(ctx.current_playing_sound).lower()
        is_same_sound = cur_norm == norm

    if is_same_hotkey and is_same_sound and is_playback_active(sound_path):
        logger.info("Stop on same hotkey: stopping (hotkey=%s)", key)
        try:
            ctx.current_playing_hotkey = None
            ctx.current_playing_sound = None
            stop_all_sounds()
            hotkey_last_stop[key] = current_time
        except Exception as e:
            logger.warning("Error stopping sounds: %s", e)
            ctx.current_playing_hotkey = None
            ctx.current_playing_sound = None
        return True
    return False


def _resolve_missing(key: str, sound_path: str) -> str | None:
    if os.path.exists(sound_path):
        return sound_path

    logger.warning("Hotkey sound file not found: %s", sound_path)
    basename = os.path.basename(sound_path)
    for category in ctx.menu:
        if isinstance(category, list) and len(category) > 0:
            candidate = os.path.join(category[0], basename)
            if os.path.exists(candidate):
                resolved = os.path.normpath(candidate)
                logger.info("Recovered missing hotkey sound at: %s", resolved)
                ctx.hotkeys[key] = resolved
                save_settings_to_config()
                return resolved

    logger.warning("Could not locate sound file for hotkey '%s': %s", key, sound_path)
    return None


def _handle_command_hotkey(key: str) -> None:
    try:
        from data.config_io import find_key
        func = find_key(ctx.KEYS_CMD, key)
        if func:
            func()
    except Exception as e:
        logger.warning("Error executing command for key '%s': %s", key, e)
