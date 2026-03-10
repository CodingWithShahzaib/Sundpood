from __future__ import annotations

import os
from time import sleep
from typing import List, Optional

import pygame as pg
import sounddevice as sd
from PyQt5 import QtCore, QtWidgets

from data.app_context import ctx
from data.config_io import jsonread, save_settings_to_config
from data.mic_passthrough import start_mic_passthrough


def get_sdl2_output_devices() -> List[str]:
    """Return output devices available to pygame (SDL2), if supported."""
    try:
        import pygame._sdl2.audio as sdl2_audio

        return list(sdl2_audio.get_audio_device_names(False))
    except Exception:
        return []


def find_device() -> Optional[str]:
    """
    Find output device for pygame and return its name (SDL2).
    Returns None if not found.
    """
    sdl2_outputs = get_sdl2_output_devices()

    try:
        sound_get_dict = jsonread(ctx.config_path)
        saved_output_device = sound_get_dict.get("output_device", None)
        if saved_output_device and saved_output_device in sdl2_outputs:
            return saved_output_device
    except Exception:
        pass

    if sdl2_outputs:
        return sdl2_outputs[0]
    return None


def sd_find_device_index(name: str, kind: str):
    """Return sounddevice index for a device name and kind ('input'/'output')."""
    try:
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            if device["name"] == name:
                if kind == "input" and device["max_input_channels"] > 0:
                    return idx
                if kind == "output" and device["max_output_channels"] > 0:
                    return idx
    except Exception:
        pass
    return None


def _restore_combo_selection(combo: QtWidgets.QComboBox, saved_text: Optional[str]) -> None:
    saved_text = str(saved_text or "").strip()
    if not saved_text:
        return

    index = combo.findText(saved_text)
    if index < 0:
        saved_lower = saved_text.lower()
        for i in range(combo.count()):
            item_text = combo.itemText(i)
            item_lower = item_text.lower()
            if item_lower == saved_lower or item_lower.startswith(saved_lower) or saved_lower in item_lower:
                index = i
                break

    if index >= 0:
        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)


def init_mixer(preferred_device: Optional[str] = None) -> Optional[str]:
    """Initialize pygame mixer for the chosen output device. Returns device name used."""
    device_name = preferred_device if preferred_device else find_device()
    try:
        pg.mixer.quit()
    except Exception:
        pass
    sleep(0.1)
    pg.mixer.pre_init(44100, -16, 2, 2048)
    try:
        if device_name:
            pg.mixer.init(devicename=device_name)
        else:
            pg.mixer.init()
        return device_name
    except Exception:
        try:
            pg.mixer.init()
            return None
        except Exception:
            return None


def populate_devices() -> None:
    """Populate output/input/virtual-mic device combos in preferences UI."""
    ctx.pref.output_device_combo.clear()
    ctx.pref.input_device_combo.clear()

    output_device_names = get_sdl2_output_devices()
    if output_device_names:
        for device_name in output_device_names:
            ctx.pref.output_device_combo.addItem(device_name)
    else:
        try:
            devices = sd.query_devices()
            for device in devices:
                if device["max_output_channels"] > 0:
                    ctx.pref.output_device_combo.addItem(device["name"])
        except Exception:
            pass

    try:
        devices = sd.query_devices()
        for device in devices:
            if device["max_input_channels"] > 0:
                ctx.pref.input_device_combo.addItem(device["name"])
    except Exception:
        pass

    ctx.pref.virtual_mic_combo.clear()
    try:
        devices = sd.query_devices()
        for device in devices:
            if device["max_output_channels"] > 0:
                ctx.pref.virtual_mic_combo.addItem(device["name"])
    except Exception:
        pass

    try:
        sound_get_dict = jsonread(ctx.config_path)
        saved_output = sound_get_dict.get("output_device", None)
        saved_input = sound_get_dict.get("input_device", None)
        saved_virtual_mic = sound_get_dict.get("virtual_mic_device", None)

        _restore_combo_selection(ctx.pref.output_device_combo, saved_output)
        _restore_combo_selection(ctx.pref.input_device_combo, saved_input)
        _restore_combo_selection(ctx.pref.virtual_mic_combo, saved_virtual_mic)
    except Exception:
        pass


def change_output_device() -> None:
    selected_device = ctx.pref.output_device_combo.currentText()
    if not selected_device:
        return

    try:
        try:
            pg.mixer.music.stop()
            pg.mixer.stop()
        except Exception:
            pass

        device_used = init_mixer(selected_device)
        if device_used is None and selected_device:
            raise RuntimeError("Selected device is not available for pygame.")

        try:
            volume = ctx.win.volume_slider.value()
            pg.mixer.music.set_volume(volume / 100)
        except Exception:
            pass

        save_settings_to_config()

        try:
            ctx.win.select_label.setText(f"✓ Output device changed to: {selected_device[:30]}...")
            ctx.win.select_label.setStyleSheet("background: rgb(50, 150, 50); color: white;")
            QtCore.QTimer.singleShot(3000, lambda: ctx.win.select_label.setStyleSheet(""))
        except Exception:
            pass
    except Exception as e:
        try:
            default_device = find_device()
            init_mixer(default_device)
            if default_device:
                index = ctx.pref.output_device_combo.findText(default_device)
                if index >= 0:
                    ctx.pref.output_device_combo.blockSignals(True)
                    ctx.pref.output_device_combo.setCurrentIndex(index)
                    ctx.pref.output_device_combo.blockSignals(False)
            save_settings_to_config()
        except Exception:
            pass

        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText("Failed to change output device")
        msg.setInformativeText(
            f"Could not initialize device: {selected_device}\n\nError: {str(e)}\n\nReverted to default device."
        )
        msg.setWindowTitle("Device Error")
        msg.exec_()


def change_virtual_mic_device() -> None:
    selected_device = ctx.pref.virtual_mic_combo.currentText()
    if selected_device:
        ctx.sound_settings["last_virtual_render_name"] = selected_device
        save_settings_to_config()
        if ctx.sound_settings.get("mic_passthrough_enabled", False):
            start_mic_passthrough()
        try:
            from data.windows_audio import sync_windows_recording_defaults

            sync_windows_recording_defaults(notify_user=False)
        except Exception:
            pass


def change_input_device() -> None:
    save_settings_to_config()
    if ctx.sound_settings.get("mic_passthrough_enabled", False):
        start_mic_passthrough()


def open_sound_folder() -> None:
    try:
        folder = os.path.abspath(getattr(ctx, "dir_", "sounds"))
        if os.path.exists(folder):
            os.startfile(folder)
    except Exception:
        pass


def test_output_device() -> None:
    try:
        test_sound = None
        for category in ctx.menu:
            if isinstance(category, list) and len(category) > 1:
                test_sound = os.path.join(category[0], category[1])
                break

        if test_sound and os.path.exists(test_sound):
            pg.mixer.music.load(test_sound)
            pg.mixer.music.play()
            ctx.win.select_label.setText("🔊 Testing headphones output...")
            ctx.win.select_label.setStyleSheet("background: rgb(70, 120, 180); color: white;")
            QtCore.QTimer.singleShot(2000, lambda: ctx.win.select_label.setStyleSheet(""))
        else:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setText("No sound files found to test")
            msg.setWindowTitle("Test Output")
            msg.exec_()
    except Exception as e:
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText(f"Failed to test output: {e}")
        msg.setWindowTitle("Test Output")
        msg.exec_()


def test_virtual_mic() -> None:
    if not ctx.sound_settings.get("virtual_mic_enabled", False):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText(
            "Virtual mic is not enabled!\n\nCheck the '✓ Send sounds to Virtual Cable' checkbox first."
        )
        msg.setWindowTitle("Virtual Mic Disabled")
        msg.exec_()
        return

    from data.virtual_mic import play_virtual_mic

    try:
        test_sound = None
        for category in ctx.menu:
            if isinstance(category, list) and len(category) > 1:
                test_sound = os.path.join(category[0], category[1])
                break

        if test_sound and os.path.exists(test_sound):
            play_virtual_mic(test_sound)
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setText(
                "Testing virtual mic!\n\nCheck your Discord/Game voice activity indicator.\nIt should show input activity."
            )
            msg.setWindowTitle("Test Virtual Mic")
            msg.exec_()
        else:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setText("No sound files found to test")
            msg.setWindowTitle("Test Virtual Mic")
            msg.exec_()
    except Exception as e:
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText(
            f"Failed to test virtual mic: {e}\n\nMake sure numpy is installed:\npip install numpy"
        )
        msg.setWindowTitle("Test Virtual Mic")
        msg.exec_()


def show_setup_guide() -> None:
    guide_text = """📖 SUNDPOOD AUDIO SETUP GUIDE

HOW IT WORKS:
1. Sounds play to YOUR HEADPHONES (so you hear them)
2. Sounds ALSO play to VIRTUAL CABLE INPUT (so Discord/Game hears them)
3. Discord/Game uses VIRTUAL CABLE OUTPUT as the microphone

SETUP STEPS:

Step 1: Install Virtual Audio Cable
• Download VB-Audio Virtual Cable from: https://vb-audio.com/Cable/
• Install it and restart if needed
• After install you'll have:
  - CABLE Input (VB-Audio Virtual Cable)
  - CABLE Output (VB-Audio Virtual Cable)

Step 2: Configure SundPood (This App)
• Open Preferences → Audio Setup tab
• "Your Headphones": Select your real headphones/speakers
• "Virtual Cable INPUT": Select "CABLE Input (VB-Audio Virtual Cable)"
• Check "✓ Send sounds to Virtual Cable"

Step 3: Configure Discord/Game
• Discord: Settings → Voice & Video
• Preferred setup: Input Device = "Default"
• Then enable SundPood's Windows mic auto-switch option
• SundPood will switch Default + Communications mic to "CABLE Output"
• On exit it restores your previous microphone automatically
• Manual fallback: set Input Device to "CABLE Output (VB-Audio Virtual Cable)"
• Output Device: Your real headphones

Step 4: Test It
• Click "Test Headphones" - You should hear sound
• Click "Test Virtual Cable" - Discord input meter should move
• Assign hotkey to a sound in main window
• Press hotkey - You AND Discord should hear it!
"""
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Information)
    msg.setText(guide_text)
    msg.setWindowTitle("Setup Guide")
    msg.setDetailedText("Full guide saved in AUDIO_SETUP_GUIDE.md")
    msg.exec_()

