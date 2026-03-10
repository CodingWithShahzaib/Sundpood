from __future__ import annotations

import os

from PyQt5 import QtWidgets, QtCore

from data import ui_overlay, ui_preferences, ui_hotkeys, ui_sundpood
from data.app_context import ctx
from data.mic_passthrough import stop_mic_passthrough
from data.library_utils import list_sound_paths
from data.playback import get_playback_progress, play_sound


class OverlayUi(QtWidgets.QMainWindow, ui_overlay.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setGeometry(QtCore.QRect(0, 0, 250, 20))
        self.setupUi(self)
        self._enhanced = False
        self._overlay_timer = None
        self._overlay_search = None
        self._overlay_list = None
        self._overlay_now = None
        self._overlay_prog = None

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_F1:
            self.hide()
            ctx.win.show()

    def enable_enhanced_overlay(self) -> None:
        """
        Upgrade overlay from a single label to a searchable sound picker with
        now-playing status. Safe to call multiple times.
        """
        if self._enhanced:
            return
        self._enhanced = True

        # Make it usable
        self.setGeometry(QtCore.QRect(20, 20, 520, 420))
        self.setMinimumSize(QtCore.QSize(420, 320))
        self.setMaximumSize(QtCore.QSize(9999, 9999))
        self.setWindowOpacity(0.95)

        # Rebuild central widget layout
        root = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self._overlay_search = QtWidgets.QLineEdit(root)
        self._overlay_search.setPlaceholderText("Search sounds… (Enter to play, F1 to close)")

        self._overlay_list = QtWidgets.QListWidget(root)
        self._overlay_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        bottom = QtWidgets.QHBoxLayout()
        self._overlay_now = QtWidgets.QLabel("", root)
        self._overlay_now.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self._overlay_prog = QtWidgets.QProgressBar(root)
        self._overlay_prog.setRange(0, 1000)
        self._overlay_prog.setValue(0)
        self._overlay_prog.setTextVisible(False)
        bottom.addWidget(self._overlay_now, 1)
        bottom.addWidget(self._overlay_prog, 1)

        layout.addWidget(self._overlay_search)
        layout.addWidget(self._overlay_list, 1)
        layout.addLayout(bottom)
        self.setCentralWidget(root)

        self._overlay_search.textChanged.connect(self._overlay_refresh)
        self._overlay_search.returnPressed.connect(self._overlay_play_selected)
        self._overlay_list.itemDoubleClicked.connect(lambda *_: self._overlay_play_selected())

        self._overlay_refresh()

        self._overlay_timer = QtCore.QTimer(self)
        self._overlay_timer.setInterval(200)
        self._overlay_timer.timeout.connect(self._overlay_tick)
        self._overlay_timer.start()

    def _overlay_refresh(self) -> None:
        if not self._overlay_list:
            return
        q = (self._overlay_search.text() if self._overlay_search else "").strip().lower()
        self._overlay_list.clear()
        for p in list_sound_paths():
            name = QtCore.QFileInfo(p).baseName()
            if q and q not in name.lower() and q not in p.lower():
                continue
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.UserRole, p)
            self._overlay_list.addItem(item)
        if self._overlay_list.count() > 0:
            self._overlay_list.setCurrentRow(0)

    def _overlay_play_selected(self) -> None:
        if not self._overlay_list:
            return
        item = self._overlay_list.currentItem()
        if not item:
            return
        p = item.data(QtCore.Qt.UserRole)
        if p:
            play_sound(p, stop_others=True)

    def _overlay_tick(self) -> None:
        try:
            cur = ctx.current_playing_sound
            if self._overlay_now is not None:
                self._overlay_now.setText(f"Now: {QtCore.QFileInfo(cur).fileName()}" if cur else "Now: —")
            if self._overlay_prog is not None:
                elapsed, dur = get_playback_progress()
                if dur > 0:
                    self._overlay_prog.setValue(int(min(1000, (elapsed / dur) * 1000)))
                else:
                    self._overlay_prog.setValue(0)
        except Exception:
            pass


class PreferencesUi(QtWidgets.QMainWindow, ui_preferences.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setupUi(self)
        self.offset = QtCore.QPoint(0, 0)

    def mousePressEvent(self, event):
        self.offset = event.pos()

    def mouseMoveEvent(self, event):
        try:
            x = event.globalX()
            y = event.globalY()
            x_w = self.offset.x()
            y_w = self.offset.y()
            self.move(x - x_w, y - y_w)
        except AttributeError:
            pass

    def closeEvent(self, event):
        from data.config_io import save_settings_to_config

        save_settings_to_config()


class HotkeysUi(QtWidgets.QMainWindow, ui_hotkeys.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setupUi(self)
        self.offset = QtCore.QPoint(0, 0)

    def mousePressEvent(self, event):
        self.offset = event.pos()

    def mouseMoveEvent(self, event):
        x = event.globalX()
        y = event.globalY()
        x_w = self.offset.x()
        y_w = self.offset.y()
        self.move(x - x_w, y - y_w)


class MainUi(QtWidgets.QMainWindow, ui_sundpood.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setupUi(self)
        self.offset = QtCore.QPoint(0, 0)
        self._setup_window_layout()

    def _setup_window_layout(self) -> None:
        self.background.setFixedHeight(45)
        self.select_label.setMinimumHeight(44)
        self.select_label.setMaximumHeight(44)

        self.play_button.setMinimumHeight(55)
        self.stop_button.setMinimumHeight(55)
        self.hkset.setMinimumHeight(55)
        self.pref_button.setFixedSize(90, 30)
        self.min_button.setFixedSize(35, 30)
        self.exit_button.setFixedSize(35, 30)

        title_layout = QtWidgets.QHBoxLayout(self.background)
        title_layout.setContentsMargins(20, 7, 10, 7)
        title_layout.setSpacing(8)
        title_layout.addWidget(self.title_label, 1)
        title_layout.addWidget(self.pref_button, 0, QtCore.Qt.AlignRight)
        title_layout.addWidget(self.min_button, 0, QtCore.Qt.AlignRight)
        title_layout.addWidget(self.exit_button, 0, QtCore.Qt.AlignRight)

        control_layout = QtWidgets.QVBoxLayout(self.control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(10)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.stop_same_hotkey_checkbox)
        control_layout.addWidget(self.hkset)
        control_layout.addSpacing(4)
        control_layout.addWidget(self.volume_label)
        control_layout.addWidget(self.volume_slider)
        control_layout.addWidget(self.volume_percent_label)
        control_layout.addSpacing(8)
        control_layout.addWidget(self.cat_label)
        control_layout.addWidget(self.catList, 1)

        sound_layout = QtWidgets.QVBoxLayout(self.sound_panel)
        sound_layout.setContentsMargins(0, 0, 0, 0)
        sound_layout.setSpacing(8)
        sound_layout.addWidget(self.sound_list_label)
        sound_layout.addWidget(self.soundList, 1)

        body_layout = QtWidgets.QHBoxLayout()
        body_layout.setSpacing(15)
        self.control_panel.setFixedWidth(320)
        self.control_panel.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        self.sound_panel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        body_layout.addWidget(self.control_panel)
        body_layout.addWidget(self.sound_panel, 1)

        content = QtWidgets.QWidget(self.centralwidget)
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(20, 10, 20, 20)
        content_layout.setSpacing(10)
        content_layout.addWidget(self.select_label)
        content_layout.addLayout(body_layout, 1)

        root_layout = QtWidgets.QVBoxLayout(self.centralwidget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(10)
        root_layout.addWidget(self.background)
        root_layout.addWidget(content, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        self.offset = event.pos()

    def mouseMoveEvent(self, event):
        try:
            x = event.globalX()
            y = event.globalY()
            x_w = self.offset.x()
            y_w = self.offset.y()
            self.move(x - x_w, y - y_w)
        except AttributeError:
            pass

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_F1:
            ctx.pref.close()
            self.hide()
            ctx.over.show()

    def closeEvent(self, event):
        # If tray mode is enabled, closing should minimize to tray unless user explicitly exits.
        try:
            tray_enabled = bool(ctx.ui_settings.get("tray_enabled", True))
        except Exception:
            tray_enabled = True
        if tray_enabled and not getattr(ctx, "tray_quitting", False):
            event.ignore()
            self.hide()
            try:
                if ctx.tray and hasattr(ctx.tray, "tray"):
                    mic_note = ""
                    if ctx.windows_capture_switch_active:
                        mic_note = (
                            "\nYour Windows mic is still routed to the virtual cable. "
                            "Right-click tray → Exit to restore it."
                        )
                    ctx.tray.tray.showMessage(
                        "SundPood",
                        f"Still running in the system tray.{mic_note}",
                        QtWidgets.QSystemTrayIcon.Information,
                        3000,
                    )
            except Exception:
                pass
            return

        from data.config_io import save_settings_to_config
        from data.playback import stop_all_sounds

        save_settings_to_config()
        if os.path.exists(".play"):
            os.remove(".play")
        try:
            stop_all_sounds()
        except Exception:
            pass
        try:
            from data.windows_audio import restore_default_recording

            restore_default_recording()
        except Exception:
            pass
        stop_mic_passthrough()
        ctx.pref.close()
        event.accept()

