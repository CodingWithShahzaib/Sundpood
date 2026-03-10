from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets


class WaveformWidget(QtWidgets.QWidget):
    """
    Simple waveform envelope widget.
    - Call `set_envelope(env, duration_ms)`
    - Click to select a time; emits `positionSelected(ms)`
    """

    trimStartSelected = QtCore.pyqtSignal(int)
    trimEndSelected = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._env: list[float] = []
        self._duration_ms: int = 0
        # Markers (ms)
        self._trim_start_ms: int | None = None
        self._trim_end_ms: int | None = None
        self.setMinimumHeight(90)

    def set_envelope(self, env: list[float], duration_ms: int) -> None:
        self._env = env or []
        self._duration_ms = max(0, int(duration_ms or 0))
        self.update()

    def set_cursor_ms(self, ms: int | None) -> None:
        """
        Backward compatible alias: sets trim start marker.
        """
        self.set_trim_markers(start_ms=ms, end_ms=self._trim_end_ms)

    def set_trim_markers(self, *, start_ms: int | None, end_ms: int | None) -> None:
        self._trim_start_ms = None if start_ms is None else max(0, int(start_ms))
        self._trim_end_ms = None if end_ms is None else max(0, int(end_ms))
        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if not self._env or self._duration_ms <= 0:
            return
        x = event.position().x() if hasattr(event, "position") else event.x()
        frac = 0.0 if self.width() <= 1 else max(0.0, min(1.0, x / float(self.width())))
        ms = int(frac * self._duration_ms)
        # Left click => trim start, Right click => trim end
        if event.button() == QtCore.Qt.RightButton:
            self._trim_end_ms = ms
            self.trimEndSelected.emit(ms)
        else:
            self._trim_start_ms = ms
            self.trimStartSelected.emit(ms)
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()

        # Background
        p.fillRect(rect, QtGui.QColor(24, 24, 28))

        if not self._env:
            p.setPen(QtGui.QColor(160, 160, 160))
            p.drawText(rect, QtCore.Qt.AlignCenter, "Waveform unavailable")
            p.end()
            return

        mid_y = rect.center().y()
        w = rect.width()
        h = rect.height()

        # Wave path (mirror around center)
        path = QtGui.QPainterPath()
        n = len(self._env)
        for i, v in enumerate(self._env):
            x = (i / max(1, n - 1)) * (w - 1)
            amp = max(0.0, min(1.0, float(v)))
            y = amp * (h * 0.45)
            if i == 0:
                path.moveTo(x, mid_y - y)
            else:
                path.lineTo(x, mid_y - y)
        for i in reversed(range(n)):
            v = self._env[i]
            x = (i / max(1, n - 1)) * (w - 1)
            amp = max(0.0, min(1.0, float(v)))
            y = amp * (h * 0.45)
            path.lineTo(x, mid_y + y)
        path.closeSubpath()

        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(88, 101, 242, 140))
        p.drawPath(path)

        # Trim region shading + markers
        if self._duration_ms > 0:
            start = self._trim_start_ms
            end = self._trim_end_ms
            if start is not None:
                start = max(0, min(self._duration_ms, int(start)))
            if end is not None:
                end = max(0, min(self._duration_ms, int(end)))

            # Shade selected region if both markers are present and valid
            if start is not None and end is not None and end > start:
                x1 = int((start / float(self._duration_ms)) * (w - 1))
                x2 = int((end / float(self._duration_ms)) * (w - 1))
                p.fillRect(QtCore.QRect(x1, rect.top(), max(1, x2 - x1), rect.height()), QtGui.QColor(255, 255, 255, 24))

            # Start marker (white)
            if start is not None:
                x = int((start / float(self._duration_ms)) * (w - 1))
                p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 220), 1))
                p.drawLine(x, rect.top() + 4, x, rect.bottom() - 4)

            # End marker (orange) (only if set and >0)
            if end is not None and end > 0:
                x = int((end / float(self._duration_ms)) * (w - 1))
                p.setPen(QtGui.QPen(QtGui.QColor(255, 170, 80, 230), 2))
                p.drawLine(x, rect.top() + 4, x, rect.bottom() - 4)

        p.end()

