from __future__ import annotations

from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QApplication

from data.app_context import ctx
from data.path_utils import resource_path


def toggle_stylesheet(path: str) -> None:
    """
    Load a QSS theme from `themes/<path>` and apply it to main + preferences windows.
    """
    app = QApplication.instance()
    if app is None:
        raise RuntimeError("No Qt Application found.")

    theme_path = resource_path("themes", path)
    file = QFile(theme_path)
    file.open(QFile.ReadOnly | QFile.Text)
    stream = QTextStream(file)
    theme = stream.readAll()

    ctx.pref.setStyleSheet(theme)
    ctx.win.setStyleSheet(theme)

    # Ensure background widget gets styled properly
    try:
        ctx.win.background.setStyleSheet("")
    except Exception:
        pass

