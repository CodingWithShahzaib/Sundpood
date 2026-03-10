from __future__ import annotations

import logging
import os
import platform
import sys
import traceback
from collections import deque
from typing import Deque, Optional

from PyQt5 import QtCore, QtWidgets

from data.app_context import ctx


class InMemoryLogHandler(logging.Handler):
    def __init__(self, capacity: int = 2000):
        super().__init__()
        self.capacity = max(200, int(capacity))
        self._lines: Deque[str] = deque(maxlen=self.capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        self._lines.append(msg)

    def get_text(self) -> str:
        return "\n".join(self._lines)

    def clear(self) -> None:
        self._lines.clear()


_handler: Optional[InMemoryLogHandler] = None


class _StreamToLogger:
    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.level = level

    def write(self, buf):
        try:
            s = str(buf)
        except Exception:
            return
        s = s.strip("\r\n")
        if s:
            self.logger.log(self.level, s)

    def flush(self):
        pass


def install_logging() -> InMemoryLogHandler:
    global _handler
    if _handler is not None:
        return _handler

    logger = logging.getLogger("sundpood")
    logger.setLevel(logging.INFO)

    handler = InMemoryLogHandler(capacity=3000)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    # Also attach to root to catch library logs
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    # Redirect stdout/stderr
    sys.stdout = _StreamToLogger(logger, logging.INFO)  # type: ignore
    sys.stderr = _StreamToLogger(logger, logging.ERROR)  # type: ignore

    def excepthook(exc_type, exc, tb):
        logger.error("Uncaught exception:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))

    sys.excepthook = excepthook
    _handler = handler
    logger.info("Diagnostics logging enabled")
    return handler


def build_diagnostics_text() -> str:
    parts = []
    parts.append("SUNDPOOD DIAGNOSTICS\n")
    parts.append(f"OS: {platform.platform()}")
    parts.append(f"Python: {sys.version.splitlines()[0]}")
    parts.append(f"CWD: {os.getcwd()}")
    parts.append("")
    try:
        import pygame

        parts.append(f"pygame: {pygame.__version__}")
    except Exception:
        parts.append("pygame: (unknown)")
    try:
        import sounddevice

        parts.append(f"sounddevice: {getattr(sounddevice, '__version__', '(unknown)')}")
    except Exception:
        parts.append("sounddevice: (unknown)")
    try:
        import PyQt5

        parts.append(f"PyQt5: {PyQt5.QtCore.PYQT_VERSION_STR}")  # type: ignore
    except Exception:
        parts.append("PyQt5: (unknown)")
    parts.append("")
    parts.append(f"Config: {getattr(ctx, 'config_path', '')}")
    parts.append(f"Theme: {getattr(ctx, 'theme', '')}")
    parts.append(f"Tray enabled: {bool(ctx.ui_settings.get('tray_enabled', True))}")
    parts.append(f"Enhanced overlay: {bool(ctx.ui_settings.get('enhanced_overlay', True))}")
    parts.append(f"Now playing: {getattr(ctx, 'current_playing_sound', None)}")
    parts.append("")
    parts.append("Sound settings:")
    for k, v in (ctx.sound_settings or {}).items():
        parts.append(f"  - {k}: {v}")
    parts.append("")
    parts.append("UI settings:")
    for k, v in (ctx.ui_settings or {}).items():
        parts.append(f"  - {k}: {v}")
    parts.append("")
    parts.append(f"Sound profiles: {len(ctx.sound_profiles or {})}")
    parts.append("")
    return "\n".join(parts)


def inject_diagnostics_tab() -> None:
    """
    Add a Diagnostics tab to Preferences.
    """
    tab = QtWidgets.QWidget()
    tab.setObjectName("diagnostics_tab")

    text = QtWidgets.QPlainTextEdit(tab)
    text.setReadOnly(True)
    text.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)

    btn_refresh = QtWidgets.QPushButton("Refresh")
    btn_copy = QtWidgets.QPushButton("Copy diagnostics")
    btn_clear = QtWidgets.QPushButton("Clear logs")

    btns = QtWidgets.QHBoxLayout()
    btns.addWidget(btn_refresh)
    btns.addWidget(btn_copy)
    btns.addWidget(btn_clear)
    btns.addStretch(1)

    layout = QtWidgets.QVBoxLayout(tab)
    layout.addLayout(btns)
    layout.addWidget(text, 1)

    handler = install_logging()

    def refresh():
        diag = build_diagnostics_text()
        logs = handler.get_text()
        text.setPlainText(diag + "\nLOGS (latest)\n" + ("-" * 40) + "\n" + logs)

    def copy():
        refresh()
        QtWidgets.QApplication.clipboard().setText(text.toPlainText())

    def clear():
        handler.clear()
        refresh()

    btn_refresh.clicked.connect(refresh)
    btn_copy.clicked.connect(copy)
    btn_clear.clicked.connect(clear)

    refresh()
    ctx.pref.tabWidget.addTab(tab, "Diagnostics")

