from __future__ import annotations

from pynput.keyboard import Listener
from PyQt5 import QtCore, QtWidgets

from data import checkbox_icon
from data.app_context import ctx
from data.config_io import save_settings_to_config
from data.device_utils import (
    change_input_device,
    change_output_device,
    change_virtual_mic_device,
    open_sound_folder,
    populate_devices,
    show_setup_guide,
    test_output_device,
    test_virtual_mic,
)
from data.hotkeys_logic import init_hotkey_bridge, key_check, key_press_handler
from data.mic_passthrough import toggle_mic_passthrough
from data.playback import change_volume, play_sound, stop_all_sounds
from data.theme_utils import toggle_stylesheet
from data.ui_actions import (
    cat_select,
    check_update,
    clear_all_hotkeys,
    filter_hotkeys,
    hotkey_delete,
    hotkey_remap,
    pref_remap,
    preview_sound,
    reset_sound_settings,
    show_sound_context_menu,
    setup_checkbox_styles,
    update_sound_setting,
)
from data.ui_settings_controls import inject_grid_settings_controls
from data.diagnostics import inject_diagnostics_tab, install_logging
from data.windows_audio import sync_windows_recording_defaults


def wire_app() -> None:
    """Wire signals/slots + start global hotkey listener."""
    # Ensure logging is installed (safe to call multiple times).
    try:
        install_logging()
    except Exception:
        pass

    # Bridge must be created on the main thread BEFORE pynput starts so
    # that QueuedConnection delivers hotkey signals to the Qt event loop.
    init_hotkey_bridge()

    key_press_listener = Listener(on_press=key_press_handler, on_release=key_check)
    key_press_listener.start()

    ctx.win.exit_button.clicked.connect(ctx.win.close)
    ctx.win.min_button.clicked.connect(ctx.win.showMinimized)
    ctx.pref.exit_button.clicked.connect(ctx.pref.close)
    ctx.pref.min_button.clicked.connect(ctx.pref.showMinimized)

    ctx.win.hkset.clicked.connect(hotkey_remap)
    ctx.win.volume_slider.valueChanged[int].connect(change_volume)

    change_volume(ctx.win.volume_slider.value())

    def show_status(text: str, ok: bool = True) -> None:
        try:
            bg = "rgb(50, 150, 50)" if ok else "rgb(170, 90, 50)"
            ctx.win.select_label.setText(text)
            ctx.win.select_label.setStyleSheet(f"background: {bg}; color: white;")
            QtCore.QTimer.singleShot(3000, lambda: ctx.win.select_label.setStyleSheet(""))
        except Exception:
            pass

    def toggle_stop_same_hotkey(state):
        try:
            ctx.sound_settings["stop_same_hotkey"] = state == QtCore.Qt.Checked
            save_settings_to_config()
        except Exception as e:
            print(f"Error saving stop_same_hotkey setting: {e}")

    try:
        ctx.win.stop_same_hotkey_checkbox.stateChanged.connect(toggle_stop_same_hotkey)
        checkbox_icon.style_checkbox(ctx.win.stop_same_hotkey_checkbox)
    except Exception as e:
        print(f"Error setting up stop_same_hotkey checkbox: {e}")

    # Tooltips
    ctx.win.play_button.setToolTip("Play the selected sound (or double-click sound)")
    ctx.win.stop_button.setToolTip("Stop all currently playing sounds")
    ctx.win.hkset.setToolTip("Assign a keyboard shortcut to the selected sound\n(Press Backspace to remove)")
    ctx.win.volume_slider.setToolTip("Adjust playback volume")
    ctx.win.catList.setToolTip("Select a category to filter sounds")
    ctx.win.soundList.setToolTip("Double-click to play, single-click to select")
    ctx.win.pref_button.setToolTip("Open settings and preferences")
    ctx.win.stop_same_hotkey_checkbox.setToolTip("Press the same hotkey again to stop the sound")

    ctx.pref.allow_overlap_checkbox.setToolTip("Allow multiple sounds to play at the same time")
    ctx.pref.loop_sounds_checkbox.setToolTip("Loop sounds continuously until stopped")
    ctx.pref.virtual_mic_checkbox.setToolTip("Send app audio to a virtual mic output device")
    ctx.pref.virtual_mic_combo.setToolTip("Select the virtual mic output device")
    ctx.pref.stop_all_button.setToolTip("Stop all currently playing sounds")
    ctx.pref.open_sound_folder_button.setToolTip("Open the sound folder")
    ctx.pref.reset_settings_button.setToolTip("Reset sound settings to defaults")
    ctx.pref.hotkeyList.setToolTip("Double-click to preview sound\nSelect and click Delete to remove")
    ctx.pref.hotkey_search.setToolTip("Filter hotkeys by name or key")
    ctx.pref.delete_button.setToolTip("Remove the selected hotkey assignment")
    ctx.pref.clear_all_button.setToolTip("Remove all hotkey assignments")
    try:
        inject_grid_settings_controls()
    except Exception:
        pass
    setup_checkbox_styles()
    if hasattr(ctx.pref, "windows_mic_autoswitch_checkbox"):
        ctx.pref.windows_mic_autoswitch_checkbox.setToolTip(
            "Keep Discord on 'Default' so SundPood can switch Windows to the selected virtual mic while the app is running."
        )
    try:
        inject_diagnostics_tab()
    except Exception:
        pass

    ctx.win.pref_button.clicked.connect(ctx.pref.show)
    ctx.win.catList.currentTextChanged.connect(lambda text: cat_select(text) if text else None)
    ctx.win.stop_button.clicked.connect(stop_all_sounds)
    ctx.win.play_button.clicked.connect(lambda *_: play_sound(False))
    ctx.win.soundList.itemDoubleClicked.connect(lambda *_: play_sound(False))

    # Sound grid context menu (quick edit/favorite/routing/hotkey)
    try:
        ctx.win.soundList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        ctx.win.soundList.customContextMenuRequested.connect(show_sound_context_menu)
    except Exception:
        pass

    # Preferences: command key remaps
    ctx.pref.play_sound.clicked.connect(lambda: pref_remap(ctx.pref.play_sound, "play_sound"))
    ctx.pref.stop_sound.clicked.connect(lambda: pref_remap(ctx.pref.stop_sound, "stop_sound"))
    ctx.pref.select_move_up.clicked.connect(lambda: pref_remap(ctx.pref.select_move_up, "select_move_up"))
    ctx.pref.select_move_down.clicked.connect(lambda: pref_remap(ctx.pref.select_move_down, "select_move_down"))
    ctx.pref.select_move_left.clicked.connect(lambda: pref_remap(ctx.pref.select_move_left, "select_move_left"))
    ctx.pref.select_move_right.clicked.connect(lambda: pref_remap(ctx.pref.select_move_right, "select_move_right"))

    ctx.pref.themesList.itemClicked.connect(lambda item: toggle_stylesheet(item.text()))
    ctx.pref.update_button.clicked.connect(check_update)

    ctx.pref.output_device_combo.currentTextChanged.connect(change_output_device)
    ctx.pref.input_device_combo.currentTextChanged.connect(change_input_device)
    ctx.pref.virtual_mic_combo.currentTextChanged.connect(change_virtual_mic_device)
    ctx.pref.refresh_devices_button.clicked.connect(populate_devices)

    def handle_mic_passthrough_toggle():
        toggle_mic_passthrough(ctx.pref.passthrough_mic_checkbox.isChecked())

    ctx.pref.passthrough_mic_checkbox.stateChanged.connect(handle_mic_passthrough_toggle)

    ctx.pref.test_output_button.clicked.connect(test_output_device)
    ctx.pref.test_virtual_button.clicked.connect(test_virtual_mic)
    ctx.pref.setup_guide_button.clicked.connect(show_setup_guide)

    ctx.pref.open_sound_folder_button.clicked.connect(open_sound_folder)
    ctx.pref.reset_settings_button.clicked.connect(reset_sound_settings)

    ctx.pref.delete_button.clicked.connect(hotkey_delete)
    ctx.pref.clear_all_button.clicked.connect(clear_all_hotkeys)

    ctx.pref.allow_overlap_checkbox.stateChanged.connect(
        lambda: update_sound_setting("allow_overlap", ctx.pref.allow_overlap_checkbox.isChecked())
    )
    ctx.pref.loop_sounds_checkbox.stateChanged.connect(
        lambda: update_sound_setting("loop_sounds", ctx.pref.loop_sounds_checkbox.isChecked())
    )

    def handle_virtual_mic_toggle():
        enabled = ctx.pref.virtual_mic_checkbox.isChecked()
        if enabled:
            try:
                import numpy as _np  # noqa: F401
            except Exception:
                ctx.pref.virtual_mic_checkbox.blockSignals(True)
                ctx.pref.virtual_mic_checkbox.setChecked(False)
                ctx.pref.virtual_mic_checkbox.blockSignals(False)
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setText("Virtual mic output requires numpy")
                msg.setInformativeText("Install numpy to enable virtual mic output.")
                msg.setWindowTitle("Virtual Mic Error")
                msg.exec_()
                update_sound_setting("virtual_mic_enabled", False)
                return
        update_sound_setting("virtual_mic_enabled", enabled)
        ok, message = sync_windows_recording_defaults(notify_user=enabled)
        if enabled and ctx.sound_settings.get("auto_switch_windows_mic", False):
            if ok:
                show_status(f"✓ Windows mic switched to: {message}", ok=True)
            else:
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setText("Windows mic auto-switch failed")
                msg.setInformativeText(
                    f"{message}\n\nDiscord should stay on the Windows 'Default' microphone for this feature."
                )
                msg.setWindowTitle("Windows Mic Auto-Switch")
                msg.exec_()

    ctx.pref.virtual_mic_checkbox.stateChanged.connect(handle_virtual_mic_toggle)

    if hasattr(ctx.pref, "windows_mic_autoswitch_checkbox"):
        def handle_windows_mic_autoswitch_toggle():
            enabled = ctx.pref.windows_mic_autoswitch_checkbox.isChecked()
            was_active = bool(ctx.windows_capture_switch_active)
            update_sound_setting("auto_switch_windows_mic", enabled)
            ok, message = sync_windows_recording_defaults(notify_user=enabled)
            if enabled and ctx.sound_settings.get("virtual_mic_enabled", False):
                if ok:
                    show_status(f"✓ Windows mic switched to: {message}", ok=True)
                else:
                    msg = QtWidgets.QMessageBox()
                    msg.setIcon(QtWidgets.QMessageBox.Warning)
                    msg.setText("Windows mic auto-switch failed")
                    msg.setInformativeText(
                        f"{message}\n\nKeep Discord input on 'Default' and choose the matching virtual cable output."
                    )
                    msg.setWindowTitle("Windows Mic Auto-Switch")
                    msg.exec_()
            elif not enabled and was_active and ok:
                show_status("✓ Restored previous Windows microphone", ok=True)

        ctx.pref.windows_mic_autoswitch_checkbox.stateChanged.connect(
            handle_windows_mic_autoswitch_toggle
        )

    ctx.pref.stop_all_button.clicked.connect(stop_all_sounds)
    ctx.pref.hotkeyList.itemDoubleClicked.connect(preview_sound)
    ctx.pref.hotkey_search.textChanged.connect(filter_hotkeys)

    ctx.win.show()

