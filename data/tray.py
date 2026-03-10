from __future__ import annotations

import os

from PyQt5 import QtCore, QtGui, QtWidgets

from data.app_context import ctx
from data.library_utils import list_sound_paths
from data.playback import play_sound, stop_all_sounds
from data.sound_profiles import is_favorite


class TrayController(QtCore.QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray = QtWidgets.QSystemTrayIcon(parent)
        self.tray.setToolTip("SundPood")
        try:
            self.tray.setIcon(QtGui.QIcon("icon.ico"))
        except Exception:
            pass

        self.menu = QtWidgets.QMenu()
        self.act_show = self.menu.addAction("Show/Hide")
        self.act_prefs = self.menu.addAction("Settings")
        self.act_overlay = self.menu.addAction("Overlay")
        self.menu.addSeparator()
        self.act_stop = self.menu.addAction("Stop all sounds")
        self.fav_menu = self.menu.addMenu("Favorites")
        self.menu.addSeparator()
        self.act_exit = self.menu.addAction("Exit")

        self.tray.setContextMenu(self.menu)

        self.act_show.triggered.connect(self.toggle_main)
        self.act_prefs.triggered.connect(self.show_prefs)
        self.act_overlay.triggered.connect(self.show_overlay)
        self.act_stop.triggered.connect(stop_all_sounds)
        self.act_exit.triggered.connect(self.exit_app)

        self.tray.activated.connect(self._on_activated)
        self.menu.aboutToShow.connect(self._rebuild_favorites)

        self._tip_timer = QtCore.QTimer(self)
        self._tip_timer.setInterval(500)
        self._tip_timer.timeout.connect(self._update_tooltip)
        self._tip_timer.start()

        self.tray.show()

    def _on_activated(self, reason):
        if reason in (QtWidgets.QSystemTrayIcon.Trigger, QtWidgets.QSystemTrayIcon.DoubleClick):
            self.toggle_main()

    def _update_tooltip(self) -> None:
        try:
            cur = ctx.current_playing_sound
            if cur:
                self.tray.setToolTip(f"SundPood\nNow: {os.path.basename(cur)}")
            else:
                self.tray.setToolTip("SundPood")
        except Exception:
            pass

    def _rebuild_favorites(self) -> None:
        self.fav_menu.clear()
        favs = [p for p in list_sound_paths() if is_favorite(p)]
        if not favs:
            act = self.fav_menu.addAction("(No favorites yet)")
            act.setEnabled(False)
            return
        for p in favs:
            name = QtCore.QFileInfo(p).baseName()
            act = self.fav_menu.addAction(name)
            act.triggered.connect(lambda checked=False, path=p: play_sound(path, stop_others=True))

    def toggle_main(self) -> None:
        if ctx.win.isVisible():
            ctx.win.hide()
        else:
            ctx.win.show()
            ctx.win.raise_()
            ctx.win.activateWindow()

    def show_prefs(self) -> None:
        ctx.pref.show()
        ctx.pref.raise_()
        ctx.pref.activateWindow()

    def show_overlay(self) -> None:
        ctx.over.show()
        ctx.over.raise_()
        ctx.over.activateWindow()

    def exit_app(self) -> None:
        # Allow the main window close handler to actually quit
        ctx.tray_quitting = True
        try:
            stop_all_sounds()
        except Exception:
            pass
        try:
            from data.windows_audio import restore_default_recording

            restore_default_recording()
        except Exception:
            pass
        try:
            self.tray.hide()
        except Exception:
            pass
        try:
            ctx.app.quit()
        except Exception:
            pass

