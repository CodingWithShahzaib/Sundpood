from __future__ import annotations

import os
from typing import Optional

from cryptography.fernet import Fernet
from pynput.keyboard import Listener
from PyQt5 import QtCore, QtGui, QtWidgets

import key
from data import checkbox_icon, keys
from data.app_context import ctx
from data.config_io import find_key, jsonread, save_settings_to_config
from data.mic_passthrough import stop_mic_passthrough, toggle_mic_passthrough
from data.playback import play_sound, stop_all_sounds
from data.theme_utils import toggle_stylesheet
from data.virtual_mic import stop_virtual_mic_playback


def select_move(mode) -> None:
    """Move selection in overlay menu."""
    ctx.select[0] += mode[0]
    ctx.select[1] += mode[1]
    if ctx.select[0] > len(ctx.menu) - 1 or ctx.select[0] < -len(ctx.menu) + 1:
        ctx.select[0] = 0
    if ctx.select[1] > len(ctx.menu[ctx.select[0]]) - 1 or ctx.select[1] < -len(ctx.menu[ctx.select[0]]) + 1:
        ctx.select[1] = 0
    if mode[0] != 0:
        ctx.select[1] = 0
    ctx.over.label.setText(ctx.menu[ctx.select[0]][ctx.select[1]])
    ctx.win.select_label.setText(ctx.menu[ctx.select[0]][ctx.select[1]])


def preview_sound(item) -> None:
    """Preview a sound from the hotkey list."""
    try:
        text = item.text()
        sound_path = text.split(":")[1].strip()
        if os.path.exists(sound_path):
            play_sound(sound_path, stop_others=True)
    except Exception:
        pass


def cat_select(cat: str) -> None:
    """
    Render the selected category into the sound list as a grid of "cards".
    (Mostly lifted from the old main.py, but using ctx instead of globals.)
    """
    ctx.win.soundList.clear()
    for i in ctx.menu:
        if "sound" + cat == i[0]:
            dir_item = QtWidgets.QListWidgetItem(i[0])
            dir_item.setData(QtCore.Qt.UserRole, i[0])
            ctx.win.soundList.addItem(dir_item)
            dir_item.setHidden(True)

            for sound_file in i:
                if sound_file == i[0]:
                    continue

                full_path = os.path.join(i[0], sound_file)
                file_name = os.path.splitext(sound_file)[0]
                file_ext = os.path.splitext(sound_file)[1]

                hotkey = find_key(ctx.hotkeys, full_path)
                if hotkey:
                    hotkey_display = f"⌨ {keys.dict_.get(hotkey, hotkey)}"
                else:
                    hotkey_display = "No hotkey"

                display_text = f"{file_name}\n{file_ext}\n{hotkey_display}"
                item = QtWidgets.QListWidgetItem(display_text)
                item.setData(QtCore.Qt.UserRole, sound_file)
                item.setData(QtCore.Qt.UserRole + 1, i[0])

                icon = QtGui.QIcon()
                card_width, card_height = 200, 160
                pixmap = QtGui.QPixmap(card_width, card_height)
                pixmap.fill(QtGui.QColor(0, 0, 0, 0))

                painter = QtGui.QPainter(pixmap)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

                if hotkey:
                    gradient = QtGui.QLinearGradient(0, 0, 0, card_height)
                    gradient.setColorAt(0, QtGui.QColor(54, 57, 63))
                    gradient.setColorAt(1, QtGui.QColor(47, 49, 54))
                    painter.setBrush(QtGui.QBrush(gradient))
                else:
                    gradient = QtGui.QLinearGradient(0, 0, 0, card_height)
                    gradient.setColorAt(0, QtGui.QColor(47, 49, 54))
                    gradient.setColorAt(1, QtGui.QColor(40, 42, 46))
                    painter.setBrush(QtGui.QBrush(gradient))

                card_rect = QtCore.QRect(4, 4, card_width - 8, card_height - 8)
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRoundedRect(card_rect, 8, 8)

                if hotkey:
                    pen = QtGui.QPen(QtGui.QColor(88, 101, 242), 2)
                    painter.setPen(pen)
                    painter.drawRoundedRect(card_rect, 8, 8)
                    pen = QtGui.QPen(QtGui.QColor(105, 116, 247, 100), 1)
                    painter.setPen(pen)
                    painter.drawRoundedRect(QtCore.QRect(5, 5, card_width - 10, card_height - 10), 7, 7)
                else:
                    pen = QtGui.QPen(QtGui.QColor(60, 63, 68), 1.5)
                    painter.setPen(pen)
                    painter.drawRoundedRect(card_rect, 8, 8)

                icon_bg_rect = QtCore.QRect(8, 8, card_width - 16, 70)
                icon_gradient = QtGui.QLinearGradient(0, 8, 0, 78)
                if hotkey:
                    icon_gradient.setColorAt(0, QtGui.QColor(88, 101, 242, 30))
                    icon_gradient.setColorAt(1, QtGui.QColor(88, 101, 242, 10))
                else:
                    icon_gradient.setColorAt(0, QtGui.QColor(60, 63, 68, 20))
                    icon_gradient.setColorAt(1, QtGui.QColor(60, 63, 68, 5))
                painter.setBrush(QtGui.QBrush(icon_gradient))
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRoundedRect(icon_bg_rect, 6, 6)

                painter.setPen(QtGui.QColor(220, 221, 222))
                painter.setFont(QtGui.QFont("Segoe UI Emoji", 42))
                icon_rect = QtCore.QRect(0, 12, card_width, 60)
                painter.drawText(icon_rect, QtCore.Qt.AlignCenter, "🔊")

                name_rect = QtCore.QRect(10, 80, card_width - 20, 35)
                painter.setFont(QtGui.QFont("Segoe UI", 11, QtGui.QFont.Bold))
                painter.setPen(QtGui.QColor(255, 255, 255))
                display_name = file_name
                if len(display_name) > 25:
                    display_name = display_name[:22] + "..."
                painter.drawText(name_rect, QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, display_name)

                ext_rect = QtCore.QRect(10, 118, 50, 18)
                ext_gradient = QtGui.QLinearGradient(10, 118, 60, 136)
                ext_gradient.setColorAt(0, QtGui.QColor(60, 63, 68))
                ext_gradient.setColorAt(1, QtGui.QColor(47, 49, 54))
                painter.setBrush(QtGui.QBrush(ext_gradient))
                painter.setPen(
                    QtGui.QPen(
                        QtGui.QColor(88, 101, 242) if hotkey else QtGui.QColor(100, 100, 100),
                        1,
                    )
                )
                painter.drawRoundedRect(ext_rect, 9, 9)
                painter.setFont(QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold))
                painter.setPen(QtGui.QColor(185, 187, 190))
                painter.drawText(ext_rect, QtCore.Qt.AlignCenter, file_ext.upper())

                if hotkey:
                    hotkey_rect = QtCore.QRect(card_width - 70, 118, 60, 18)
                    hotkey_gradient = QtGui.QLinearGradient(card_width - 70, 118, card_width - 10, 136)
                    hotkey_gradient.setColorAt(0, QtGui.QColor(88, 101, 242))
                    hotkey_gradient.setColorAt(1, QtGui.QColor(71, 82, 196))
                    painter.setBrush(QtGui.QBrush(hotkey_gradient))
                    painter.setPen(QtCore.Qt.NoPen)
                    painter.drawRoundedRect(hotkey_rect, 9, 9)
                    painter.setFont(QtGui.QFont("Segoe UI", 9, QtGui.QFont.Bold))
                    painter.setPen(QtGui.QColor(255, 255, 255))
                    hotkey_text = keys.dict_.get(hotkey, hotkey).upper()
                    painter.drawText(hotkey_rect, QtCore.Qt.AlignCenter, hotkey_text)
                else:
                    no_hotkey_rect = QtCore.QRect(card_width - 70, 118, 60, 18)
                    painter.setFont(QtGui.QFont("Segoe UI", 7))
                    painter.setPen(QtGui.QColor(100, 100, 100))
                    painter.drawText(no_hotkey_rect, QtCore.Qt.AlignCenter, "No key")

                info_bar_rect = QtCore.QRect(8, card_height - 22, card_width - 16, 14)
                info_gradient = QtGui.QLinearGradient(8, card_height - 22, card_width - 8, card_height - 8)
                info_gradient.setColorAt(0, QtGui.QColor(40, 42, 46, 150))
                info_gradient.setColorAt(1, QtGui.QColor(32, 34, 37, 150))
                painter.setBrush(QtGui.QBrush(info_gradient))
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRoundedRect(info_bar_rect, 3, 3)

                painter.end()

                icon.addPixmap(pixmap)
                item.setIcon(icon)
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                ctx.win.soundList.addItem(item)


def hotkey_remap() -> None:
    """Assign hotkey to the currently selected sound (UX dialog + listener)."""
    try:
        current_item = ctx.win.soundList.currentItem()
        if not current_item:
            raise AttributeError("No item selected")

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
                raise AttributeError("Could not find directory path")

        sound = os.path.normpath(sound)
        sound_name = actual_filename
    except AttributeError:
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText("Please select a sound first!")
        msg.setWindowTitle("No Sound Selected")
        msg.exec_()
        return

    hotkey_remap_listener: Optional[Listener] = None

    def check(k):
        nonlocal hotkey_remap_listener
        k = str(k).replace("'", "")

        if k not in keys.forbidden:
            if k in ctx.hotkeys.keys():
                old_sound = os.path.basename(ctx.hotkeys[k])
                if hotkey_remap_listener:
                    hotkey_remap_listener.stop()

                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Question)
                msg.setText(
                    f"Key '{keys.dict_.get(k, k)}' is already assigned to:\n{old_sound}\n\nReassign to {sound_name}?"
                )
                msg.setWindowTitle("Key Already Assigned")
                msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if msg.exec_() != QtWidgets.QMessageBox.Yes:
                    try:
                        ctx.win.hkset.setEnabled(True)
                        ctx.win.hkset.setText("⌨ Assign Hotkey")
                        ctx.win.select_label.setText("")
                        ctx.win.select_label.setStyleSheet("")
                    except Exception:
                        pass
                    return False

            ctx.hotkeys.update({k: sound})
            try:
                ctx.win.select_label.setText(
                    f"✓ Hotkey '{keys.dict_.get(k, k)}' assigned to {sound_name}"
                )
                ctx.win.select_label.setStyleSheet("background: rgb(50, 150, 50); color: white;")
            except Exception:
                pass

        elif k == "Key.backspace":
            if hotkey_remap_listener:
                try:
                    hotkey_remap_listener.stop()
                except Exception:
                    pass

            existing_key = find_key(ctx.hotkeys, sound)
            if existing_key:
                del ctx.hotkeys[existing_key]
                try:
                    ctx.win.select_label.setText(f"✓ Hotkey removed from {sound_name}")
                    ctx.win.select_label.setStyleSheet("background: rgb(200, 100, 50); color: white;")
                except Exception:
                    pass

        if hotkey_remap_listener:
            try:
                hotkey_remap_listener.stop()
            except Exception:
                pass

        try:
            save_settings_to_config()
            ctx.pref.hotkeyList.clear()
            config_data = jsonread(ctx.config_path)
            sounds_data = config_data.get("sounds", [])
            for i in sounds_data:
                for x in i:
                    x = os.path.join(i[0], x)
                    if x in ctx.hotkeys.values():
                        ctx.pref.hotkeyList.addItem(f"{find_key(ctx.hotkeys, x)}\t:{x}")

            ctx.win.hkset.setEnabled(True)
            ctx.win.hkset.setText("⌨ Assign Hotkey")

            try:
                current_cat = ctx.win.catList.currentItem()
                if current_cat:
                    ctx.win.soundList.blockSignals(True)
                    ctx.win.catList.blockSignals(True)
                    try:
                        cat_select(current_cat.text())
                    finally:
                        ctx.win.soundList.blockSignals(False)
                        ctx.win.catList.blockSignals(False)
            except Exception as e:
                print(f"Error refreshing sound list: {e}")

            QtCore.QTimer.singleShot(3000, lambda: ctx.win.select_label.setStyleSheet(""))
        except Exception as e:
            print(f"Error in hotkey assignment: {e}")
            try:
                ctx.win.hkset.setEnabled(True)
                ctx.win.hkset.setText("⌨ Assign Hotkey")
            except Exception:
                pass

        return False

    ctx.win.hkset.setEnabled(False)
    ctx.win.hkset.setText("⌨ Press any key...")
    ctx.win.select_label.setText(
        f"🎯 Assigning hotkey to: {sound_name}\n(Press Backspace to remove existing hotkey)"
    )
    ctx.win.select_label.setStyleSheet("background: rgb(70, 120, 180); color: white;")

    hotkey_remap_listener = Listener(on_release=check)
    hotkey_remap_listener.start()


def hotkey_delete() -> None:
    try:
        k = ctx.pref.hotkeyList.currentItem().text().split(":")[0].replace("\t", "")
        ctx.hotkeys.pop(k)
        save_settings_to_config()
        ctx.pref.hotkeyList.clear()
        config_data = jsonread(ctx.config_path)
        sounds_data = config_data.get("sounds", [])
        for i in sounds_data:
            for x in i:
                x = os.path.join(i[0], x)
                if x in ctx.hotkeys.values():
                    ctx.pref.hotkeyList.addItem(f"{find_key(ctx.hotkeys, x)}\t:{x}")
    except Exception:
        pass


def pref_remap(btn, func_: str) -> None:
    """Remap a command key inside Preferences."""

    def check(k):
        k = str(k).replace("'", "")
        if k not in keys.forbidden:
            ctx.KEYS_CMD.update({find_key(ctx.COMMAND_DICT, func_): k})
            btn.setText(keys.dict_.get(k, k))
        elif k == "Key.backspace":
            ctx.KEYS_CMD.update({find_key(ctx.COMMAND_DICT, func_): " "})
            btn.setText(" ")
        for b in ctx.PREF_BTN:
            b.setEnabled(True)
        save_settings_to_config()
        return False

    for b in ctx.PREF_BTN:
        b.setEnabled(False)

    listener = Listener(on_release=check)
    listener.start()


def filter_hotkeys(text: str) -> None:
    for i in range(ctx.pref.hotkeyList.count()):
        item = ctx.pref.hotkeyList.item(i)
        item.setHidden(text.lower() not in item.text().lower())


def clear_all_hotkeys() -> None:
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Question)
    msg.setText("Are you sure you want to clear all hotkeys?")
    msg.setWindowTitle("Confirm Clear All")
    msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

    if msg.exec_() == QtWidgets.QMessageBox.Yes:
        ctx.hotkeys.clear()
        ctx.pref.hotkeyList.clear()
        save_settings_to_config()


def update_sound_setting(k: str, value) -> None:
    ctx.sound_settings[k] = value
    save_settings_to_config()


def reset_sound_settings() -> None:
    ctx.sound_settings["allow_overlap"] = True
    ctx.sound_settings["loop_sounds"] = False
    ctx.sound_settings["virtual_mic_enabled"] = False
    ctx.sound_settings["mic_passthrough_enabled"] = False
    try:
        ctx.pref.allow_overlap_checkbox.setChecked(True)
        ctx.pref.loop_sounds_checkbox.setChecked(False)
        ctx.pref.virtual_mic_checkbox.setChecked(False)
        ctx.pref.passthrough_mic_checkbox.setChecked(False)
    except Exception:
        pass

    stop_virtual_mic_playback()
    stop_mic_passthrough()
    save_settings_to_config()

    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Information)
    msg.setText("All settings have been reset to defaults!")
    msg.setWindowTitle("Settings Reset")
    msg.exec_()


def check_update() -> str:
    def decrypt(filename, k):
        f = Fernet(k)
        with open(filename, "rb") as file:
            encrypted_data = file.read()
        decrypted_data = f.decrypt(encrypted_data)
        return decrypted_data.decode("utf-8")

    file_ = decrypt(os.path.join("data", "sundpood-runtime.sr"), key.KEY)
    version = ""
    for i in file_:
        if i != "/":
            version += i
        else:
            break
    print(ctx.VERSION)
    return version.split(" ")[3]


def setup_checkbox_styles() -> None:
    """Apply custom checkbox styling."""
    checkbox_icon.style_checkbox(ctx.pref.virtual_mic_checkbox)
    checkbox_icon.style_checkbox(ctx.pref.passthrough_mic_checkbox)
    try:
        checkbox_icon.style_checkbox(ctx.pref.allow_overlap_checkbox)
        checkbox_icon.style_checkbox(ctx.pref.loop_sounds_checkbox)
    except Exception:
        pass
    try:
        checkbox_icon.style_checkbox(ctx.win.stop_same_hotkey_checkbox)
    except Exception:
        pass

