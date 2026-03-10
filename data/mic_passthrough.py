from __future__ import annotations

import queue
import threading

import sounddevice as sd
from PyQt5 import QtWidgets

from data.app_context import ctx
from data.config_io import save_settings_to_config

# Mic passthrough variables (separate streams for better compatibility)
mic_passthrough_input_stream = None
mic_passthrough_output_stream = None
mic_passthrough_buffer = None
mic_passthrough_running = threading.Event()
mic_passthrough_samplerate = None
mic_passthrough_channels = 2
_virtual_mix_lock = threading.Lock()
_virtual_mix_layers = []


def virtual_output_is_active() -> bool:
    return mic_passthrough_output_stream is not None


def _resample_audio(arr, input_rate: int, output_rate: int):
    import numpy as np

    if not input_rate or not output_rate or int(input_rate) == int(output_rate):
        return arr.astype(np.float32, copy=False)

    source = np.asarray(arr, dtype=np.float32)
    if len(source) == 0:
        return source

    old_positions = np.arange(len(source), dtype=np.float32)
    new_length = max(1, int(round(len(source) * float(output_rate) / float(input_rate))))
    new_positions = np.linspace(0, max(0, len(source) - 1), new_length, dtype=np.float32)

    if source.ndim == 1:
        return np.interp(new_positions, old_positions, source).astype(np.float32)

    channels = []
    for idx in range(source.shape[1]):
        channels.append(np.interp(new_positions, old_positions, source[:, idx]))
    return np.stack(channels, axis=1).astype(np.float32)


def _prepare_virtual_mix_audio(arr, samplerate: int):
    import numpy as np

    prepared = np.asarray(arr, dtype=np.float32)
    if prepared.ndim == 1:
        prepared = prepared[:, None]
    if prepared.ndim == 2 and prepared.shape[1] > mic_passthrough_channels:
        prepared = prepared[:, :mic_passthrough_channels]
    if prepared.ndim == 2 and prepared.shape[1] < mic_passthrough_channels:
        if prepared.shape[1] == 1:
            prepared = np.repeat(prepared, mic_passthrough_channels, axis=1)
        else:
            pad_width = mic_passthrough_channels - prepared.shape[1]
            prepared = np.pad(prepared, ((0, 0), (0, pad_width)))
    prepared = _resample_audio(prepared, int(samplerate), int(mic_passthrough_samplerate or samplerate))
    return np.ascontiguousarray(prepared, dtype=np.float32)


def enqueue_virtual_mix_audio(arr, samplerate: int, *, loop: bool = False) -> bool:
    if not virtual_output_is_active():
        return False

    prepared = _prepare_virtual_mix_audio(arr, samplerate)
    with _virtual_mix_lock:
        _virtual_mix_layers.append(
            {
                "data": prepared,
                "position": 0,
                "loop": bool(loop),
            }
        )
    return True


def clear_virtual_mix_audio() -> None:
    with _virtual_mix_lock:
        _virtual_mix_layers.clear()


def mix_virtual_audio_into(outdata) -> None:
    import numpy as np

    with _virtual_mix_lock:
        if not _virtual_mix_layers:
            return

        finished = []
        for layer in _virtual_mix_layers:
            data = layer["data"]
            position = int(layer["position"])
            frame_offset = 0

            while frame_offset < len(outdata):
                remaining = len(data) - position
                if remaining <= 0:
                    if layer["loop"]:
                        position = 0
                        remaining = len(data)
                    else:
                        finished.append(layer)
                        break

                block = min(remaining, len(outdata) - frame_offset)
                outdata[frame_offset:frame_offset + block] += data[position:position + block]
                position += block
                frame_offset += block

            layer["position"] = position

        if finished:
            _virtual_mix_layers[:] = [layer for layer in _virtual_mix_layers if layer not in finished]

    np.clip(outdata, -1.0, 1.0, out=outdata)


def start_mic_passthrough() -> None:
    """
    Routes microphone input to virtual output device using separate streams.
    """
    global mic_passthrough_input_stream, mic_passthrough_output_stream
    global mic_passthrough_buffer, mic_passthrough_running
    global mic_passthrough_samplerate, mic_passthrough_channels

    stop_mic_passthrough()

    if not ctx.sound_settings.get("mic_passthrough_enabled", False):
        return

    input_name = ctx.pref.input_device_combo.currentText()
    virtual_output_name = ctx.pref.virtual_mic_combo.currentText()
    if not input_name or not virtual_output_name:
        return

    from data.device_utils import sd_find_device_index

    input_index = sd_find_device_index(input_name, "input")
    output_index = sd_find_device_index(virtual_output_name, "output")

    if input_index is None or output_index is None:
        ctx.pref.passthrough_mic_checkbox.setChecked(False)
        ctx.sound_settings["mic_passthrough_enabled"] = False
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText("Failed to start mic passthrough")
        msg.setInformativeText(
            f"Could not find devices:\nInput: {input_name}\nOutput: {virtual_output_name}"
        )
        msg.setWindowTitle("Mic Passthrough Error")
        msg.exec_()
        return

    try:
        input_info = sd.query_devices(input_index)
        output_info = sd.query_devices(output_index)

        input_rate = int(input_info.get("default_samplerate", 48000))
        output_rate = int(output_info.get("default_samplerate", 48000))

        common_rates = [48000, 44100, 32000, 24000, 22050, 16000]
        samplerate = 48000
        for rate in common_rates:
            if abs(input_rate - rate) < 1000 or abs(output_rate - rate) < 1000:
                samplerate = rate
                break

        channels = 2
        mic_passthrough_samplerate = samplerate
        mic_passthrough_channels = channels

        print(f"Mic passthrough config: {samplerate}Hz, {channels}ch")
        print(f"Input: {input_name} (default: {input_rate}Hz)")
        print(f"Output: {virtual_output_name} (default: {output_rate}Hz)")
    except Exception as e:
        ctx.pref.passthrough_mic_checkbox.setChecked(False)
        ctx.sound_settings["mic_passthrough_enabled"] = False
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText("Failed to query device information")
        msg.setInformativeText(f"Error: {str(e)}\n\nPlease check your device settings.")
        msg.setWindowTitle("Mic Passthrough Error")
        msg.exec_()
        return

    try:
        import numpy as np
    except Exception:
        ctx.pref.passthrough_mic_checkbox.setChecked(False)
        ctx.sound_settings["mic_passthrough_enabled"] = False
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText("Microphone passthrough requires numpy")
        msg.setInformativeText("Please install numpy:\n\npip install numpy\n\nThen restart the application.")
        msg.setWindowTitle("Missing Dependency")
        msg.exec_()
        return

    mic_passthrough_buffer = queue.Queue(maxsize=10)
    mic_passthrough_running.set()

    def input_callback(indata, frames, time_info, status):
        if status:
            status_str = str(status)
            if "overflow" not in status_str.lower() and "underflow" not in status_str.lower():
                print(f"Input status: {status}")
        try:
            if indata.shape[1] == 1 and channels == 2:
                stereo_data = np.repeat(indata, 2, axis=1)
                mic_passthrough_buffer.put(stereo_data.copy(), block=False)
            else:
                mic_passthrough_buffer.put(indata.copy(), block=False)
        except queue.Full:
            pass

    def output_callback(outdata, frames, time_info, status):
        if status:
            status_str = str(status)
            if "overflow" not in status_str.lower() and "underflow" not in status_str.lower():
                print(f"Output status: {status}")
        outdata.fill(0)
        try:
            data = mic_passthrough_buffer.get(block=False)
            outdata[:] = data
        except queue.Empty:
            pass
        try:
            mix_virtual_audio_into(outdata)
        except Exception as e:
            print(f"Virtual mix callback error: {e}")

    try:
        try:
            mic_passthrough_input_stream = sd.InputStream(
                samplerate=samplerate,
                channels=min(input_info.get("max_input_channels", 2), 2),
                dtype="float32",
                device=input_index,
                callback=input_callback,
                blocksize=2048,
            )
            mic_passthrough_input_stream.start()
            print(f"✓ Input stream started: {input_name}")
        except Exception as e:
            raise Exception(f"Failed to open input device: {str(e)}")

        try:
            mic_passthrough_output_stream = sd.OutputStream(
                samplerate=samplerate,
                channels=channels,
                dtype="float32",
                device=output_index,
                callback=output_callback,
                blocksize=2048,
            )
            mic_passthrough_output_stream.start()
            print(f"✓ Output stream started: {virtual_output_name}")
        except Exception as e:
            if mic_passthrough_input_stream:
                mic_passthrough_input_stream.stop()
                mic_passthrough_input_stream.close()
                mic_passthrough_input_stream = None
            raise Exception(f"Failed to open output device: {str(e)}")

        print(f"✓ Mic passthrough active: {input_name} -> {virtual_output_name}")
    except Exception as e:
        mic_passthrough_input_stream = None
        mic_passthrough_output_stream = None
        mic_passthrough_buffer = None
        mic_passthrough_running.clear()

        ctx.pref.passthrough_mic_checkbox.setChecked(False)
        ctx.sound_settings["mic_passthrough_enabled"] = False
        save_settings_to_config()

        error_msg = str(e)
        helpful_text = "🎤 MICROPHONE PASSTHROUGH SETUP:\n\n"

        if (
            "combination" in error_msg.lower()
            or "9993" in error_msg
            or "opening" in error_msg.lower()
        ):
            helpful_text += "⚠️ Device Compatibility Issue:\n\n"
            helpful_text += "Your microphone and virtual cable use different audio\n"
            helpful_text += "drivers that cannot be combined directly.\n\n"
            helpful_text += "✓ ALTERNATIVE SOLUTION:\n"
            helpful_text += "Use Windows Sound Settings instead:\n\n"
            helpful_text += "1. Right-click Speaker icon → Sounds\n"
            helpful_text += "2. Go to 'Recording' tab\n"
            helpful_text += "3. Select your Microphone → Properties\n"
            helpful_text += "4. Go to 'Listen' tab\n"
            helpful_text += "5. Check 'Listen to this device'\n"
            helpful_text += "6. Select 'CABLE Input' as playback device\n"
            helpful_text += "7. Click Apply → OK\n\n"
            helpful_text += "This will route your mic through the virtual cable.\n"
        else:
            helpful_text += "• Make sure devices are not in use by another app\n"
            helpful_text += "• Try restarting the application\n"
            helpful_text += "• Check your audio driver settings\n"

        helpful_text += f"\n📋 Technical: {error_msg}"

        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Microphone Passthrough Setup")
        msg.setInformativeText(helpful_text)
        msg.setWindowTitle("Mic Passthrough - Alternative Solution")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg.exec_()


def stop_mic_passthrough() -> None:
    global mic_passthrough_input_stream, mic_passthrough_output_stream
    global mic_passthrough_buffer, mic_passthrough_running
    global mic_passthrough_samplerate, mic_passthrough_channels

    mic_passthrough_running.clear()

    try:
        if mic_passthrough_input_stream:
            mic_passthrough_input_stream.stop()
            mic_passthrough_input_stream.close()
    except Exception:
        pass

    try:
        if mic_passthrough_output_stream:
            mic_passthrough_output_stream.stop()
            mic_passthrough_output_stream.close()
    except Exception:
        pass

    mic_passthrough_input_stream = None
    mic_passthrough_output_stream = None
    mic_passthrough_buffer = None
    mic_passthrough_samplerate = None
    mic_passthrough_channels = 2
    clear_virtual_mix_audio()
    print("Mic passthrough stopped")


def toggle_mic_passthrough(enabled: bool) -> None:
    ctx.sound_settings["mic_passthrough_enabled"] = enabled
    save_settings_to_config()
    if enabled:
        start_mic_passthrough()
    else:
        stop_mic_passthrough()

