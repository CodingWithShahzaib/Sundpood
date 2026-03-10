from __future__ import annotations

import threading
from typing import Optional

import sounddevice as sd
from PyQt5 import QtWidgets

from data.app_context import ctx
from data.config_io import save_settings_to_config
from data.mic_passthrough import (
    clear_virtual_mix_audio,
    enqueue_virtual_mix_audio,
    virtual_output_is_active,
)

virtual_mic_stop = threading.Event()
virtual_mic_thread: Optional[threading.Thread] = None
_virtual_mic_generation = 0


def stop_virtual_mic_playback(wait: bool = True) -> None:
    global virtual_mic_thread, _virtual_mic_generation

    _virtual_mic_generation += 1
    virtual_mic_stop.set()
    clear_virtual_mix_audio()

    try:
        sd.stop()
    except Exception:
        pass

    thread = virtual_mic_thread
    if wait and thread and thread.is_alive() and thread is not threading.current_thread():
        try:
            thread.join(timeout=1.0)
        except Exception:
            pass

    if thread is None or not thread.is_alive():
        virtual_mic_thread = None


def _has_numpy() -> bool:
    try:
        import numpy as _np  # noqa: F401

        return True
    except Exception:
        return False


def play_virtual_mic(sound_path: str, loop: bool = False, *, arr=None, samplerate: int | None = None) -> None:
    """
    Send app audio to the configured virtual output.

    Normal one-shot sounds avoid creating worker threads entirely. If microphone
    passthrough is active, app audio is mixed into that existing output stream
    instead of competing for the same device with another sounddevice stream.
    """
    global virtual_mic_thread, _virtual_mic_generation

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

    if arr is None or samplerate is None:
        try:
            from data.audio_processing import load_sound_array

            samplerate, arr = load_sound_array(sound_path)
        except Exception as e:
            print(f"Failed to prepare virtual mic audio: {e}")
            return

    try:
        if hasattr(arr, "ndim") and arr.ndim == 2 and arr.shape[1] >= 2:
            arr = arr.mean(axis=1)
        arr = np.asarray(arr, dtype=np.float32)
        print(f"Playing to virtual device: {virtual_device_name} (index: {virtual_device_index})")
    except Exception as e:
        print(f"Failed to normalize virtual mic audio: {e}")
        return

    if virtual_output_is_active():
        if enqueue_virtual_mix_audio(arr, int(samplerate), loop=loop):
            return

    stop_virtual_mic_playback(wait=bool(loop))
    virtual_mic_stop.clear()

    if not loop:
        try:
            sd.play(arr, samplerate=int(samplerate), device=virtual_device_index, blocking=False)
        except Exception as e:
            print(f"Virtual mic playback error: {e}")
        return

    _virtual_mic_generation += 1
    run_generation = _virtual_mic_generation

    def worker() -> None:
        global virtual_mic_thread
        try:
            while not virtual_mic_stop.is_set() and run_generation == _virtual_mic_generation:
                try:
                    sd.play(arr, samplerate=int(samplerate), device=virtual_device_index)
                    sd.wait()
                except Exception as e:
                    print(f"Virtual mic playback error: {e}")
                    break
                if virtual_mic_stop.is_set() or run_generation != _virtual_mic_generation:
                    break
        finally:
            if virtual_mic_thread is threading.current_thread():
                virtual_mic_thread = None

    virtual_mic_thread = threading.Thread(target=worker, daemon=True, name="virtual-mic-loop")
    virtual_mic_thread.start()

