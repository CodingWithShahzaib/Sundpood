from __future__ import annotations

import os
import time

import pygame as pg
from PyQt5 import QtCore

from data.app_context import ctx
from data.sound_profiles import get_profile
from data.sound_profiles import set_profile
from data.virtual_mic import play_virtual_mic, stop_virtual_mic_playback

# Track local pygame sound playback for stop/seek/progress.
_active_sound_obj = None
_active_channel = None
_play_started_at = None
_play_duration_ms = None
_play_looping = False


def _current_volume_scalar() -> float:
    try:
        return max(0.0, min(1.0, ctx.win.volume_slider.value() / 100.0))
    except Exception:
        try:
            return float(pg.mixer.music.get_volume())
        except Exception:
            return 0.7


def _set_playback_progress(duration_ms: int | None, *, loop: bool = False) -> None:
    global _play_started_at, _play_duration_ms, _play_looping
    _play_started_at = time.monotonic()
    _play_duration_ms = int(duration_ms or 0)
    _play_looping = bool(loop)


def change_volume(value: int) -> None:
    pg.mixer.music.set_volume(value / 100)
    try:
        if _active_channel:
            _active_channel.set_volume(value / 100)
    except Exception:
        pass
    try:
        ctx.win.volume_percent_label.setText(f"{value}%")
    except Exception:
        pass


def _is_main_thread() -> bool:
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QThread
        app = QApplication.instance()
        return app is not None and QThread.currentThread() == app.thread()
    except Exception:
        return True


def _do_update_status(sound_path: str | None) -> None:
    try:
        if sound_path:
            ctx.win.select_label.setStyleSheet("background: rgb(50, 150, 50); color: white;")
            sound_name = os.path.basename(sound_path) if sound_path else ""
            ctx.win.select_label.setText(f"▶ {sound_name}")
        else:
            ctx.win.select_label.setStyleSheet("")
            if ctx.menu and len(ctx.menu) > 0 and len(ctx.menu[ctx.select[0]]) > ctx.select[1]:
                ctx.win.select_label.setText(ctx.menu[ctx.select[0]][ctx.select[1]])
    except Exception:
        pass


def update_playing_status(sound_path: str | None) -> None:
    if _is_main_thread():
        _do_update_status(sound_path)
    else:
        try:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: _do_update_status(sound_path))
        except Exception:
            pass


def _normalized_path(path: str | None) -> str:
    try:
        return os.path.normpath(os.path.abspath(str(path or ""))).lower()
    except Exception:
        return os.path.normpath(str(path or "")).lower()


def is_playback_active(sound_path: str | None = None) -> bool:
    current_sound = getattr(ctx, "current_playing_sound", None)
    if not current_sound:
        return False
    if sound_path and _normalized_path(sound_path) != _normalized_path(current_sound):
        return False

    try:
        if _active_channel and _active_channel.get_busy():
            return True
    except Exception:
        pass

    try:
        if pg.mixer.music.get_busy():
            return True
    except Exception:
        pass

    if _play_looping:
        return True

    if _play_started_at is None:
        return False

    if _play_duration_ms and _play_duration_ms > 0:
        elapsed_ms = int((time.monotonic() - float(_play_started_at)) * 1000)
        return elapsed_ms < (_play_duration_ms + 120)

    return False


def play_sound(*argv, loop: bool | None = None, stop_others: bool = True, start_ms: int | None = None):
    """
    Play a sound. Supports being called as `play_sound(False)` from UI to
    play the currently selected item.
    """
    if False in argv:
        try:
            current_item = ctx.win.soundList.currentItem()
            if not current_item:
                return False

            actual_filename = current_item.data(QtCore.Qt.UserRole)
            directory_path = current_item.data(QtCore.Qt.UserRole + 1)
            sound = current_item.data(QtCore.Qt.UserRole + 2)

            if sound:
                sound = os.path.normpath(sound)
            elif actual_filename and directory_path:
                sound = os.path.join(directory_path, actual_filename)
            else:
                return False
        except AttributeError as e:
            print(f"Error getting sound path: {e}")
            return False
    else:
        sound = os.path.normpath(argv[0])

    if not pg.mixer.get_init():
        try:
            from data.device_utils import init_mixer
            from data.config_io import jsonread

            preferred_device = None
            try:
                preferred_device = jsonread(ctx.config_path).get("output_device", None)
            except Exception:
                pass
            init_mixer(preferred_device)
        except Exception as e:
            print(f"Failed to initialize mixer: {e}")
            return False

    if not os.path.exists(sound):
        print(f"Sound file not found: {sound}")
        if os.path.basename(sound) == sound and not os.path.dirname(sound):
            for category in ctx.menu:
                if isinstance(category, list) and len(category) > 0:
                    dir_path = category[0]
                    potential_path = os.path.join(dir_path, sound)
                    if os.path.exists(potential_path):
                        sound = potential_path
                        print(f"Found sound at: {sound}")
                        break
            else:
                print(f"Could not locate sound file: {sound}")
                return False
        else:
            return False

    prof = get_profile(sound)
    route = (prof.get("route") or "both").lower()
    play_local = route in ("both", "local")
    play_virtual = route in ("both", "virtual")

    # Default looping: global loop setting OR explicit loop arg.
    loop_enabled = bool(ctx.sound_settings.get("loop_sounds", False) if loop is None else loop)

    # Stop previous sounds if needed
    if stop_others:
        stop_all_sounds()

    # Prefer numpy processing pipeline (enables trim/fade/speed/pan)
    try:
        from data.audio_processing import float_to_int16, process_sound, duration_ms
        samplerate, arr_f, _ = process_sound(
            sound,
            start_ms_override=start_ms,
            use_loop_region=loop_enabled,
        )
        dur_ms = duration_ms(samplerate, arr_f)

        ok = True
        global _active_sound_obj, _active_channel

        if play_local:
            arr_i16 = float_to_int16(arr_f)
            _active_sound_obj = pg.sndarray.make_sound(arr_i16)
            loops = -1 if loop_enabled else 0
            _active_channel = _active_sound_obj.play(loops=loops)
            if _active_channel:
                _active_channel.set_volume(_current_volume_scalar())

        if play_virtual:
            play_virtual_mic(sound, loop=loop_enabled, arr=arr_f, samplerate=samplerate)

        _set_playback_progress(dur_ms, loop=loop_enabled)
        update_playing_status(sound)
        ctx.current_playing_sound = os.path.normpath(sound)
        try:
            set_profile(sound, {"last_played_ts": float(time.time())})
        except Exception:
            pass
        return ok
    except Exception as e:
        # Fallback to original behavior if processing fails
        print(f"Advanced playback failed, falling back: {e}")

    try:
        # Legacy path: pygame music + optional virtual mic decode
        fallback_duration_ms = None
        try:
            fallback_duration_ms = int(pg.mixer.Sound(sound).get_length() * 1000)
        except Exception:
            pass
        if play_local:
            try:
                pg.mixer.music.load(sound)
                loops = -1 if loop_enabled else 0
                if start_ms and start_ms > 0:
                    try:
                        pg.mixer.music.play(loops=loops, start=start_ms / 1000.0)
                    except Exception:
                        pg.mixer.music.play(loops=loops)
                else:
                    pg.mixer.music.play(loops=loops)
            except Exception:
                sound_obj = pg.mixer.Sound(sound)
                loops = -1 if loop_enabled else 0
                sound_obj.set_volume(pg.mixer.music.get_volume())
                _active_sound_obj = sound_obj
                _active_channel = sound_obj.play(loops=loops)

        if play_virtual:
            play_virtual_mic(sound, loop=loop_enabled)

        _set_playback_progress(fallback_duration_ms, loop=loop_enabled)
        update_playing_status(sound)
        ctx.current_playing_sound = os.path.normpath(sound)
        return True
    except Exception as e:
        print(f"Error playing sound: {e}")
        return False


def stop_all_sounds() -> None:
    global _active_channel, _active_sound_obj, _play_started_at, _play_duration_ms, _play_looping
    try:
        pg.mixer.music.stop()
    except Exception as e:
        print(f"Error stopping music: {e}")

    try:
        pg.mixer.stop()
    except Exception as e:
        print(f"Error stopping mixer: {e}")

    try:
        if _active_channel:
            _active_channel.stop()
    except Exception:
        pass
    _active_channel = None
    _active_sound_obj = None
    _play_started_at = None
    _play_duration_ms = None
    _play_looping = False

    try:
        stop_virtual_mic_playback()
    except Exception as e:
        print(f"Error stopping virtual mic playback: {e}")

    try:
        update_playing_status(None)
    except Exception as e:
        print(f"Error updating playing status: {e}")

    ctx.current_playing_sound = None
    ctx.current_playing_hotkey = None


def get_playback_progress() -> tuple[int, int]:
    """Return (elapsed_ms, duration_ms) best-effort for UI (overlay/tray)."""
    if _play_started_at is None or _play_duration_ms is None:
        return (0, 0)
    elapsed = max(0, int((time.monotonic() - float(_play_started_at)) * 1000))
    return (elapsed, int(_play_duration_ms))

