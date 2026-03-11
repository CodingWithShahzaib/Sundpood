from __future__ import annotations

import logging
import os
from typing import Optional

from pynput.keyboard import Listener
from PyQt5 import QtCore, QtGui, QtWidgets

from data import checkbox_icon, keys
from data.app_context import ctx
from data.config_io import find_key, jsonread, normalize_sound_path, save_settings_to_config
from data.mic_passthrough import stop_mic_passthrough
from data.playback import play_sound, stop_all_sounds
from data.theme_utils import toggle_stylesheet
from data.virtual_mic import stop_virtual_mic_playback
from data.sound_profiles import is_favorite, toggle_favorite
from data.sound_editor import SoundEditorDialog
from data.library_utils import category_display_name

logger = logging.getLogger("sundpood.ui")


def select_move(mode) -> None:
    """Move selection in overlay menu."""
    if not ctx.menu:
        try:
            ctx.win.select_label.setText("No sounds available")
        except Exception:
            pass
        return

    ctx.select[0] += mode[0]
    ctx.select[1] += mode[1]
    if ctx.select[0] > len(ctx.menu) - 1 or ctx.select[0] < -len(ctx.menu) + 1:
        ctx.select[0] = 0
    if ctx.select[1] > len(ctx.menu[ctx.select[0]]) - 1 or ctx.select[1] < -len(ctx.menu[ctx.select[0]]) + 1:
        ctx.select[1] = 0
    if mode[0] != 0:
        ctx.select[1] = 0
    label_text = ctx.menu[ctx.select[0]][ctx.select[1]]
    if not getattr(ctx.over, "_enhanced", False):
        try:
            ctx.over.label.setText(label_text)
        except Exception:
            pass
    ctx.win.select_label.setText(label_text)


def preview_sound(item) -> None:
    """Preview a sound from the hotkey list."""
    try:
        sound_path = item.data(QtCore.Qt.UserRole + 1)
        if not sound_path:
            sound_path = item.text().partition("\t:")[2].strip()
        sound_path = normalize_sound_path(sound_path)
        if os.path.exists(sound_path):
            play_sound(sound_path, loop=False, stop_others=True)
    except Exception:
        pass


def build_hotkey_list_item(key_str: str, sound_path: str) -> QtWidgets.QListWidgetItem:
    sound_path = normalize_sound_path(sound_path)
    item = QtWidgets.QListWidgetItem(f"{key_str}\t: {sound_path}")
    item.setData(QtCore.Qt.UserRole, key_str)
    item.setData(QtCore.Qt.UserRole + 1, sound_path)
    return item


def refresh_current_category() -> None:
    try:
        current_cat = ctx.win.catList.currentItem()
        if current_cat and current_cat.text():
            cat_select(current_cat.text())
    except Exception as exc:
        logger.debug("Failed to refresh current category: %s", exc)


def select_sound_in_grid(sound_path: str | None) -> None:
    """
    Switch to the category containing the sound and highlight it in the grid.
    Called when playback starts (e.g. via hotkey) so the user sees which sound is playing.
    """
    if not sound_path or not ctx.menu:
        return
    try:
        norm_path = os.path.normpath(sound_path).lower()
        for cat in ctx.menu:
            if not isinstance(cat, list) or len(cat) < 2:
                continue
            dir_path = cat[0]
            for sound_file in cat[1:]:
                full = os.path.normpath(os.path.join(dir_path, sound_file)).lower()
                if full == norm_path:
                    cat_name = category_display_name(dir_path)
                    current_cat = ctx.win.catList.currentItem()
                    if not current_cat or current_cat.text() != cat_name:
                        for i in range(ctx.win.catList.count()):
                            if ctx.win.catList.item(i).text() == cat_name:
                                ctx.win.catList.setCurrentRow(i)
                                cat_select(cat_name)
                                break
                    for i in range(ctx.win.soundList.count()):
                        item = ctx.win.soundList.item(i)
                        p = get_item_sound_path(item)
                        if p and os.path.normpath(p).lower() == norm_path:
                            ctx.win.soundList.setCurrentItem(item)
                            ctx.win.soundList.scrollToItem(item)
                            return
                    return
    except Exception as exc:
        logger.debug("Failed to select sound in grid: %s", exc)


def refresh_hotkey_list() -> None:
    ctx.pref.hotkeyList.clear()
    config_data = jsonread(ctx.config_path) or {}
    for category in config_data.get("sounds", []):
        if not isinstance(category, list) or len(category) < 2:
            continue
        dir_path = normalize_sound_path(category[0])
        for sound_name in category[1:]:
            sound_path = normalize_sound_path(os.path.join(dir_path, sound_name))
            key_str = find_key(ctx.hotkeys, sound_path)
            if key_str:
                ctx.pref.hotkeyList.addItem(build_hotkey_list_item(key_str, sound_path))


def cat_select(cat: str) -> None:
    """
    Render the selected category into the sound list as a grid of "cards".
    (Mostly lifted from the old main.py, but using ctx instead of globals.)
    """
    ctx.win.soundList.clear()
    for i in ctx.menu:
        if category_display_name(i[0]) == cat:
            dir_item = QtWidgets.QListWidgetItem(i[0])
            dir_item.setData(QtCore.Qt.UserRole, i[0])
            ctx.win.soundList.addItem(dir_item)
            dir_item.setHidden(True)

            # Apply grid customization
            try:
                base = int(ctx.ui_settings.get("grid_card_size", 200) or 200)
                pad = int(ctx.ui_settings.get("grid_padding", 20) or 20)
                spacing = int(ctx.ui_settings.get("grid_spacing", 15) or 15)
                card_width, card_height = base, int(base * 0.8)
                ctx.win.soundList.setIconSize(QtCore.QSize(card_width, card_height))
                ctx.win.soundList.setGridSize(QtCore.QSize(card_width + pad, card_height + pad))
                ctx.win.soundList.setSpacing(spacing)
            except Exception:
                card_width, card_height = 200, 160

            # Build list so we can sort/favorites-first
            entries = []
            for sound_file in i:
                if sound_file == i[0]:
                    continue
                full_path = os.path.normpath(os.path.join(i[0], sound_file))
                file_name = os.path.splitext(sound_file)[0]
                file_ext = os.path.splitext(sound_file)[1]

                hotkey = find_key(ctx.hotkeys, full_path)
                hotkey_display = f"⌨ {keys.dict_.get(hotkey, hotkey)}" if hotkey else "No hotkey"
                fav = is_favorite(full_path)
                entries.append(
                    {
                        "sound_file": sound_file,
                        "full_path": full_path,
                        "file_name": file_name,
                        "file_ext": file_ext,
                        "hotkey": hotkey,
                        "hotkey_display": hotkey_display,
                        "favorite": fav,
                    }
                )

            sort_mode = (ctx.ui_settings.get("grid_sort") or "name").lower()
            favorites_first = bool(ctx.ui_settings.get("favorites_first", True))

            def _sort_key(d):
                if sort_mode == "ext":
                    return (d["file_ext"].lower(), d["file_name"].lower())
                if sort_mode == "hotkey":
                    hk = keys.dict_.get(d["hotkey"], d["hotkey"]) if d["hotkey"] else ""
                    return (0 if d["hotkey"] else 1, str(hk).lower(), d["file_name"].lower())
                if sort_mode == "recent":
                    try:
                        from data.sound_profiles import get_profile

                        ts = float(get_profile(d["full_path"]).get("last_played_ts", 0.0) or 0.0)
                    except Exception:
                        ts = 0.0
                    return (-ts, d["file_name"].lower())
                if sort_mode == "none":
                    return (0,)
                return (d["file_name"].lower(), d["file_ext"].lower())

            if sort_mode != "none":
                entries.sort(key=_sort_key)
            if favorites_first:
                entries.sort(key=lambda d: (not d["favorite"],))

            for d in entries:
                full_path = d["full_path"]
                hotkey = d["hotkey"]
                file_ext = d["file_ext"]
                file_name = d["file_name"]

                name_for_list = ("★ " + file_name) if d["favorite"] else file_name
                display_text = f"{name_for_list}\n{file_ext}\n{d['hotkey_display']}"
                item = QtWidgets.QListWidgetItem(display_text)
                item.setData(QtCore.Qt.UserRole, d["sound_file"])
                item.setData(QtCore.Qt.UserRole + 1, i[0])
                item.setData(QtCore.Qt.UserRole + 2, full_path)

                icon = QtGui.QIcon()
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

                if d["favorite"]:
                    pen = QtGui.QPen(QtGui.QColor(250, 200, 60), 2)
                    painter.setPen(pen)
                    painter.drawRoundedRect(card_rect, 8, 8)
                elif hotkey:
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


def get_item_sound_path(item) -> str | None:
    try:
        p = item.data(QtCore.Qt.UserRole + 2)
        if p:
            return os.path.normpath(p)
    except Exception:
        pass
    # Fallback
    try:
        actual_filename = item.data(QtCore.Qt.UserRole)
        directory_path = item.data(QtCore.Qt.UserRole + 1)
        if actual_filename and directory_path:
            return os.path.normpath(os.path.join(directory_path, actual_filename))
    except Exception:
        pass
    return None


def open_sound_editor_for_item(item) -> None:
    sound_path = get_item_sound_path(item)
    if not sound_path:
        return
    dlg = SoundEditorDialog(sound_path, parent=ctx.win)
    dlg.exec_()


def show_sound_context_menu(pos) -> None:
    item = ctx.win.soundList.itemAt(pos)
    if not item:
        return
    sound_path = get_item_sound_path(item)

    menu = QtWidgets.QMenu(ctx.win.soundList)

    act_play = menu.addAction("▶ Play")
    act_stop = menu.addAction("■ Stop all")
    menu.addSeparator()

    fav_label = "★ Unfavorite" if (sound_path and is_favorite(sound_path)) else "☆ Favorite"
    act_fav = menu.addAction(fav_label)
    act_edit = menu.addAction("⚙ Edit sound settings…")
    menu.addSeparator()
    act_hotkey = menu.addAction("⌨ Assign hotkey to this sound…")

    menu.addSeparator()
    route_menu = menu.addMenu("Output routing")
    act_route_both = route_menu.addAction("Both (Headphones + Virtual)")
    act_route_local = route_menu.addAction("Local only (Headphones)")
    act_route_virtual = route_menu.addAction("Virtual only (Cable)")

    chosen = menu.exec_(ctx.win.soundList.mapToGlobal(pos))
    if not chosen:
        return

    from data.playback import play_sound, stop_all_sounds
    from data.sound_profiles import set_profile

    if chosen == act_play and sound_path:
        ctx.win.soundList.setCurrentItem(item)
        play_sound(sound_path, stop_others=True)
    elif chosen == act_stop:
        stop_all_sounds()
    elif chosen == act_fav and sound_path:
        toggle_favorite(sound_path)
        save_settings_to_config()
        # Refresh current category UI so badges can reflect updated state
        try:
            cur = ctx.win.catList.currentItem()
            if cur:
                cat_select(cur.text())
        except Exception:
            pass
    elif chosen == act_edit:
        open_sound_editor_for_item(item)
    elif chosen == act_hotkey:
        # Select item first then reuse existing flow
        ctx.win.soundList.setCurrentItem(item)
        hotkey_remap()
    elif chosen in (act_route_both, act_route_local, act_route_virtual) and sound_path:
        if chosen == act_route_both:
            set_profile(sound_path, {"route": "both"})
        elif chosen == act_route_local:
            set_profile(sound_path, {"route": "local"})
        else:
            set_profile(sound_path, {"route": "virtual"})
        save_settings_to_config()


def hotkey_remap() -> None:
    """Assign hotkey to the currently selected sound (UX dialog + listener)."""
    try:
        current_item = ctx.win.soundList.currentItem()
        if not current_item:
            raise AttributeError("No item selected")

        sound = get_item_sound_path(current_item)
        if not sound:
            raise AttributeError("Could not resolve sound path")

        sound = normalize_sound_path(sound)
        sound_name = os.path.splitext(os.path.basename(sound))[0]
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
            refresh_hotkey_list()

            ctx.win.hkset.setEnabled(True)
            ctx.win.hkset.setText("⌨ Assign Hotkey")

            try:
                ctx.win.soundList.blockSignals(True)
                ctx.win.catList.blockSignals(True)
                try:
                    refresh_current_category()
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
    item = ctx.pref.hotkeyList.currentItem()
    if not item:
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Please select a hotkey to remove.")
        msg.setWindowTitle("No Hotkey Selected")
        msg.exec_()
        return

    hotkey = item.data(QtCore.Qt.UserRole) or item.text().partition("\t:")[0].replace("\t", "")
    ctx.hotkeys.pop(hotkey, None)
    save_settings_to_config()
    refresh_hotkey_list()
    refresh_current_category()


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
        refresh_current_category()


def update_sound_setting(k: str, value) -> None:
    ctx.sound_settings[k] = value
    save_settings_to_config()


def reset_sound_settings() -> None:
    ctx.sound_settings["allow_overlap"] = True
    ctx.sound_settings["loop_sounds"] = False
    ctx.sound_settings["virtual_mic_enabled"] = False
    ctx.sound_settings["mic_passthrough_enabled"] = False
    ctx.sound_settings["auto_switch_windows_mic"] = False
    try:
        ctx.pref.allow_overlap_checkbox.setChecked(True)
        ctx.pref.loop_sounds_checkbox.setChecked(False)
        ctx.pref.virtual_mic_checkbox.setChecked(False)
        ctx.pref.passthrough_mic_checkbox.setChecked(False)
        if hasattr(ctx.pref, "windows_mic_autoswitch_checkbox"):
            ctx.pref.windows_mic_autoswitch_checkbox.setChecked(False)
    except Exception:
        pass

    stop_virtual_mic_playback()
    stop_mic_passthrough()
    try:
        from data.windows_audio import sync_windows_recording_defaults

        sync_windows_recording_defaults(notify_user=False)
    except Exception:
        pass
    save_settings_to_config()

    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Information)
    msg.setText("All settings have been reset to defaults!")
    msg.setWindowTitle("Settings Reset")
    msg.exec_()


def check_update() -> str:
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Information)
    msg.setText("Update checking is not configured in this build.")
    msg.setInformativeText(
        f"SundPood version: {ctx.VERSION}\n\nThe app no longer uses the old encrypted runtime update check."
    )
    msg.setWindowTitle("Check for Updates")
    msg.exec_()
    return str(ctx.VERSION)


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
        if hasattr(ctx.pref, "windows_mic_autoswitch_checkbox"):
            checkbox_icon.style_checkbox(ctx.pref.windows_mic_autoswitch_checkbox)
    except Exception:
        pass
    try:
        checkbox_icon.style_checkbox(ctx.win.stop_same_hotkey_checkbox)
    except Exception:
        pass

