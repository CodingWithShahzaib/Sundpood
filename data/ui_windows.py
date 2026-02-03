from __future__ import annotations

import os

from PyQt5 import QtWidgets, QtCore

from data import ui_overlay, ui_preferences, ui_hotkeys, ui_sundpood
from data.app_context import ctx
from data.mic_passthrough import stop_mic_passthrough


class OverlayUi(QtWidgets.QMainWindow, ui_overlay.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setGeometry(QtCore.QRect(0, 0, 250, 20))
        self.setupUi(self)

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_F1:
            self.hide()
            ctx.win.show()


class PreferencesUi(QtWidgets.QMainWindow, ui_preferences.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setupUi(self)

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
        # Make background widget resize with window
        self.background.setParent(self.centralwidget)

    def resizeEvent(self, event):
        """Update UI elements when window is resized."""
        super().resizeEvent(event)
        width = event.size().width()
        height = event.size().height()

        if hasattr(self, "background"):
            self.background.setGeometry(QtCore.QRect(0, 0, width, 45))

        if hasattr(self, "exit_button"):
            self.exit_button.setGeometry(QtCore.QRect(width - 45, 7, 35, 30))
        if hasattr(self, "min_button"):
            self.min_button.setGeometry(QtCore.QRect(width - 85, 7, 35, 30))
        if hasattr(self, "pref_button"):
            self.pref_button.setGeometry(QtCore.QRect(width - 180, 7, 90, 30))

        if hasattr(self, "select_label"):
            self.select_label.setGeometry(QtCore.QRect(20, 55, width - 40, 40))

        if hasattr(self, "control_panel"):
            self.control_panel.setGeometry(QtCore.QRect(20, 105, 320, height - 115))

        if hasattr(self, "sound_panel"):
            self.sound_panel.setGeometry(QtCore.QRect(355, 105, width - 375, height - 115))

        if hasattr(self, "soundList"):
            self.soundList.setGeometry(
                QtCore.QRect(0, 40, self.sound_panel.width(), self.sound_panel.height() - 40)
            )

        if hasattr(self, "catList"):
            self.catList.setGeometry(QtCore.QRect(0, 335, 320, self.control_panel.height() - 335))

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
        from data.config_io import save_settings_to_config
        from data.playback import stop_all_sounds

        save_settings_to_config()
        if os.path.exists(".play"):
            os.remove(".play")
        try:
            stop_all_sounds()
        except Exception:
            pass
        stop_mic_passthrough()
        ctx.pref.close()

