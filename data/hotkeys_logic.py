from __future__ import annotations

import os
import threading
from time import time

import pygame as pg

from data.app_context import ctx
from data.config_io import save_settings_to_config
from data.playback import play_sound, stop_all_sounds

# Global state for sound management / hotkeys
pressed_keys = set()
push_to_talk_enabled = {}

hotkey_last_press = {}
hotkey_last_stop = {}
hotkey_lock = threading.Lock()
HOTKEY_DEBOUNCE_TIME = 0.15
HOTKEY_STOP_DEBOUNCE_TIME = 0.3


def key_press_handler(key) -> None:
    """Handle key down (push-to-talk only)."""
    key = str(key).replace("'", "")
    if key in ctx.hotkeys.keys() and push_to_talk_enabled.get(key, False):
        if key not in pressed_keys:
            pressed_keys.add(key)
            play_sound(ctx.hotkeys[key], loop=True, stop_others=False)


def key_check(key) -> None:
    """Handle key up: normal hotkeys + command hotkeys."""
    key = str(key).replace("'", "")

    if key in pressed_keys:
        pressed_keys.remove(key)
        try:
            stop_all_sounds()
        except Exception as e:
            print(f"Error stopping sounds on push-to-talk release: {e}")
        return

    if key in ctx.hotkeys.keys():
        current_time = time()
        last_press_time = hotkey_last_press.get(key, 0)
        if current_time - last_press_time < HOTKEY_DEBOUNCE_TIME:
            return

        if not hotkey_lock.acquire(blocking=False):
            return

        try:
            hotkey_last_press[key] = current_time
            sound_path = os.path.normpath(ctx.hotkeys[key])

            print(f"Hotkey pressed: {key} -> {sound_path}")

            stop_on_same = ctx.sound_settings.get("stop_same_hotkey", False)
            if stop_on_same:
                last_stop_time = hotkey_last_stop.get(key, 0)
                if current_time - last_stop_time < HOTKEY_STOP_DEBOUNCE_TIME:
                    return

                try:
                    try:
                        abs_sound_path = os.path.abspath(sound_path)
                    except Exception:
                        abs_sound_path = os.path.normpath(sound_path)
                    normalized_sound_path = os.path.normpath(abs_sound_path).lower()

                    is_same_hotkey = ctx.current_playing_hotkey == key
                    is_same_sound = False
                    if ctx.current_playing_sound:
                        try:
                            abs_current = os.path.abspath(ctx.current_playing_sound)
                        except Exception:
                            abs_current = os.path.normpath(ctx.current_playing_sound)
                        normalized_current = os.path.normpath(abs_current).lower()
                        is_same_sound = normalized_current == normalized_sound_path

                    is_music_busy = False
                    try:
                        is_music_busy = pg.mixer.music.get_busy()
                    except Exception:
                        pass

                    if is_same_hotkey:
                        print(
                            "Debug: "
                            f"same_hotkey={is_same_hotkey}, "
                            f"same_sound={is_same_sound}, "
                            f"music_busy={is_music_busy}, "
                            f"current_hotkey={ctx.current_playing_hotkey}, "
                            f"current_sound={ctx.current_playing_sound}"
                        )

                    if is_same_hotkey and (is_same_sound or is_music_busy):
                        print(
                            f"Stop on same hotkey: Stopping current sound (hotkey={key}, sound={sound_path})"
                        )
                        try:
                            ctx.current_playing_hotkey = None
                            ctx.current_playing_sound = None
                            stop_all_sounds()
                            hotkey_last_stop[key] = current_time
                        except Exception as e:
                            print(f"Error stopping sounds: {e}")
                            ctx.current_playing_hotkey = None
                            ctx.current_playing_sound = None
                        return
                except Exception as e:
                    print(f"Error checking if same sound is playing: {e}")

            overlap_allowed = ctx.sound_settings.get("allow_overlap", True)
            loop_enabled = ctx.sound_settings.get("loop_sounds", False)

            if not os.path.exists(sound_path):
                print(f"Hotkey sound file not found: {sound_path}")
                sound_basename = os.path.basename(sound_path)
                found = False
                for category in ctx.menu:
                    if isinstance(category, list) and len(category) > 0:
                        dir_path = category[0]
                        potential_path = os.path.join(dir_path, sound_basename)
                        if os.path.exists(potential_path):
                            sound_path = os.path.normpath(potential_path)
                            print(f"Found sound at: {sound_path}")
                            ctx.hotkeys[key] = sound_path
                            save_settings_to_config()
                            found = True
                            break
                if not found:
                    print(f"Could not locate sound file for hotkey '{key}': {sound_path}")
                    return

            try:
                print(f"Playing sound: {sound_path}")
                ctx.current_playing_hotkey = key
                result = play_sound(sound_path, loop=loop_enabled, stop_others=not overlap_allowed)
                if result:
                    if not ctx.current_playing_sound:
                        ctx.current_playing_sound = os.path.normpath(sound_path)
                else:
                    ctx.current_playing_hotkey = None
                    ctx.current_playing_sound = None
            except Exception as e:
                print(f"Error playing sound from hotkey '{key}': {e}")
                ctx.current_playing_hotkey = None
                ctx.current_playing_sound = None
        finally:
            hotkey_lock.release()
    elif key in ctx.KEYS_CMD.values():
        try:
            from data.config_io import find_key

            func = find_key(ctx.KEYS_CMD, key)
            if func:
                func()
        except Exception as e:
            print(f"Error executing command for key '{key}': {e}")

