from __future__ import annotations

import threading
from typing import Optional

import pygame as pg
import sounddevice as sd
from PyQt5 import QtWidgets

from data.app_context import ctx
from data.config_io import save_settings_to_config

virtual_mic_stop = threading.Event()
virtual_mic_thread: Optional[threading.Thread] = None


def stop_virtual_mic_playback() -> None:
    global virtual_mic_thread
    try:
        virtual_mic_stop.set()
        if virtual_mic_thread and virtual_mic_thread.is_alive():
            try:
                sd.stop()
            except Exception:
                pass
    finally:
        virtual_mic_thread = None


def _has_numpy() -> bool:
    try:
        import numpy as _np  # noqa: F401

        return True
    except Exception:
        return False


def play_virtual_mic(sound_path: str, loop: bool = False) -> None:
    """
    Sends app audio to the selected virtual mic output device using sounddevice.
    """
    if not ctx.sound_settings.get("virtual_mic_enabled", False):
        return

    virtual_device_name = ctx.pref.virtual_mic_combo.currentText()
    if not virtual_device_name:
        return

    from data.device_utils import sd_find_device_index

    virtual_device_index = sd_find_device_index(virtual_device_name, "output")
    if virtual_device_index is None:
        print(f"Could not find virtual device: {virtual_device_name}")
        return

    if not _has_numpy():
        try:
            ctx.pref.virtual_mic_checkbox.blockSignals(True)
            ctx.pref.virtual_mic_checkbox.setChecked(False)
            ctx.pref.virtual_mic_checkbox.blockSignals(False)
        except Exception:
            pass
        ctx.sound_settings["virtual_mic_enabled"] = False
        save_settings_to_config()
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText("Virtual mic output requires numpy")
        msg.setInformativeText("Install numpy to enable virtual mic output.")
        msg.setWindowTitle("Virtual Mic Error")
        msg.exec_()
        return

    import numpy as np

    try:
        snd = pg.mixer.Sound(sound_path)
        arr = pg.sndarray.array(snd)
        freq, fmt, channels = pg.mixer.get_init()
        if arr.dtype != np.float32:
            arr = arr.astype(np.float32) / 32768.0
        if channels == 1 and arr.ndim == 2:
            arr = arr[:, 0]
        elif channels == 2 and arr.ndim == 2:
            arr = arr.mean(axis=1)
        print(f"Playing to virtual device: {virtual_device_name} (index: {virtual_device_index})")
    except Exception as e:
        print(f"Failed to prepare virtual mic audio: {e}")
        return

    def worker():
        virtual_mic_stop.clear()
        while True:
            try:
                sd.play(arr, samplerate=freq, device=virtual_device_index)
                sd.wait()
            except Exception as e:
                print(f"Virtual mic playback error: {e}")
                break
            if not loop or virtual_mic_stop.is_set():
                break

    stop_virtual_mic_playback()
    global virtual_mic_thread
    virtual_mic_thread = threading.Thread(target=worker, daemon=True)
    virtual_mic_thread.start()

