from __future__ import annotations

import os

import pygame as pg
from PyQt5 import QtCore

from data.app_context import ctx
from data.virtual_mic import play_virtual_mic, stop_virtual_mic_playback


def change_volume(value: int) -> None:
    pg.mixer.music.set_volume(value / 100)
    try:
        ctx.win.volume_percent_label.setText(f"{value}%")
    except Exception:
        pass


def update_playing_status(sound_path: str | None) -> None:
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


def play_sound(*argv, loop: bool = False, stop_others: bool = True):
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

            if not actual_filename:
                actual_filename = current_item.text().split("[")[0].strip()

            if directory_path:
                sound = os.path.join(directory_path, actual_filename)
            else:
                first_item = ctx.win.soundList.item(0)
                if first_item:
                    directory_path = first_item.data(QtCore.Qt.UserRole) or first_item.text()
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

    try:
        if stop_others:
            pg.mixer.music.stop()
            pg.mixer.stop()
    except Exception:
        pass

    try:
        try:
            pg.mixer.music.load(sound)
            loops = -1 if loop else 0
            pg.mixer.music.play(loops=loops)
        except Exception:
            sound_obj = pg.mixer.Sound(sound)
            loops = -1 if loop else 0
            sound_obj.set_volume(pg.mixer.music.get_volume())
            sound_obj.play(loops=loops)

        update_playing_status(sound)
        ctx.current_playing_sound = os.path.normpath(sound)

        play_virtual_mic(sound, loop=loop)
        return True
    except RuntimeError as e:
        print(f"Runtime error playing sound: {e}")
        return False
    except Exception as e:
        print(f"Error playing sound: {e}")
        return False


def stop_all_sounds() -> None:
    try:
        pg.mixer.music.stop()
    except Exception as e:
        print(f"Error stopping music: {e}")

    try:
        pg.mixer.stop()
    except Exception as e:
        print(f"Error stopping mixer: {e}")

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

