from __future__ import annotations

import os
from typing import Dict

from PyQt5 import QtCore, QtWidgets

from data.audio_processing import duration_ms, load_sound_array, waveform_envelope
from data.config_io import save_settings_to_config
from data.playback import play_sound, stop_all_sounds
from data.sound_profiles import get_profile, set_profile
from data.waveform_widget import WaveformWidget


class SoundEditorDialog(QtWidgets.QDialog):
    def __init__(self, sound_path: str, parent=None):
        super().__init__(parent)
        self.sound_path = os.path.normpath(sound_path)
        self.setWindowTitle(f"Sound Settings - {os.path.basename(self.sound_path)}")
        self.setMinimumSize(720, 520)

        self.profile: Dict = get_profile(self.sound_path)

        self.wave = WaveformWidget(self)
        self.wave.trimStartSelected.connect(self._on_wave_left_click)
        self.wave.trimEndSelected.connect(self._on_wave_right_click)

        # Controls
        self.favorite = QtWidgets.QCheckBox("★ Favorite")
        self.route = QtWidgets.QComboBox()
        self.route.addItems(["both", "local", "virtual"])

        self.volume = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.volume.setRange(0, 200)
        self.pan = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.pan.setRange(-100, 100)

        self.speed = QtWidgets.QDoubleSpinBox()
        self.speed.setRange(0.25, 4.0)
        self.speed.setSingleStep(0.05)
        self.speed.setDecimals(2)

        self.pitch = QtWidgets.QDoubleSpinBox()
        self.pitch.setRange(-12.0, 12.0)
        self.pitch.setSingleStep(0.5)
        self.pitch.setDecimals(1)

        self.fade_in = QtWidgets.QSpinBox()
        self.fade_in.setRange(0, 10000)
        self.fade_out = QtWidgets.QSpinBox()
        self.fade_out.setRange(0, 10000)
        self.trim_start = QtWidgets.QSpinBox()
        self.trim_start.setRange(0, 3600_000)
        self.trim_end = QtWidgets.QSpinBox()
        self.trim_end.setRange(0, 3600_000)
        self.loop_start = QtWidgets.QSpinBox()
        self.loop_start.setRange(0, 3600_000)
        self.loop_end = QtWidgets.QSpinBox()
        self.loop_end.setRange(0, 3600_000)

        self.btn_play = QtWidgets.QPushButton("▶ Preview")
        self.btn_stop = QtWidgets.QPushButton("■ Stop")
        self.btn_apply = QtWidgets.QPushButton("Save")
        self.btn_close = QtWidgets.QPushButton("Close")

        self.btn_play.clicked.connect(self._preview)
        self.btn_stop.clicked.connect(stop_all_sounds)
        self.btn_apply.clicked.connect(self._save)
        self.btn_close.clicked.connect(self.close)

        form = QtWidgets.QFormLayout()
        form.addRow("Favorite", self.favorite)
        form.addRow("Output routing", self.route)
        form.addRow("Volume (%)", self.volume)
        form.addRow("Pan (L/R)", self.pan)
        form.addRow("Speed (simple)", self.speed)
        form.addRow("Pitch semitones (simple)", self.pitch)
        form.addRow("Fade in (ms)", self.fade_in)
        form.addRow("Fade out (ms)", self.fade_out)
        form.addRow("Trim start (ms)", self.trim_start)
        form.addRow("Trim end (ms, 0=none)", self.trim_end)
        form.addRow("Loop start (ms)", self.loop_start)
        form.addRow("Loop end (ms, 0=none)", self.loop_end)

        loop_note = QtWidgets.QLabel("Loop markers are only used when looping is enabled during playback.")
        loop_note.setWordWrap(True)

        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(self.btn_play)
        btns.addWidget(self.btn_stop)
        btns.addStretch(1)
        btns.addWidget(self.btn_apply)
        btns.addWidget(self.btn_close)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.wave)
        layout.addLayout(form)
        layout.addWidget(loop_note)
        layout.addLayout(btns)

        self._load_waveform()
        self._load_profile_into_widgets()
        self._wire_marker_updates()

    def _load_waveform(self) -> None:
        try:
            sr, arr = load_sound_array(self.sound_path)
            dur = duration_ms(sr, arr)
            env = waveform_envelope(arr, points=700)
            self.wave.set_envelope(env, dur)
        except Exception:
            self.wave.set_envelope([], 0)

    def _load_profile_into_widgets(self) -> None:
        p = self.profile
        self.favorite.setChecked(bool(p.get("favorite", False)))
        route = (p.get("route") or "both").lower()
        idx = self.route.findText(route)
        self.route.setCurrentIndex(idx if idx >= 0 else 0)

        self.volume.setValue(int(round(float(p.get("volume", 1.0) or 1.0) * 100)))
        self.pan.setValue(int(round(float(p.get("pan", 0.0) or 0.0) * 100)))
        self.speed.setValue(float(p.get("speed", 1.0) or 1.0))
        self.pitch.setValue(float(p.get("pitch_semitones", 0.0) or 0.0))

        self.fade_in.setValue(int(p.get("fade_in_ms", 0) or 0))
        self.fade_out.setValue(int(p.get("fade_out_ms", 0) or 0))
        self.trim_start.setValue(int(p.get("trim_start_ms", 0) or 0))
        self.trim_end.setValue(int(p.get("trim_end_ms", 0) or 0))
        self.loop_start.setValue(int(p.get("loop_start_ms", 0) or 0))
        self.loop_end.setValue(int(p.get("loop_end_ms", 0) or 0))

        self.wave.set_trim_markers(
            start_ms=int(p.get("trim_start_ms", 0) or 0),
            end_ms=int(p.get("trim_end_ms", 0) or 0),
        )

    def _wire_marker_updates(self) -> None:
        def update_markers():
            self.wave.set_trim_markers(
                start_ms=int(self.trim_start.value()),
                end_ms=int(self.trim_end.value()),
            )

        self.trim_start.valueChanged.connect(lambda *_: update_markers())
        self.trim_end.valueChanged.connect(lambda *_: update_markers())
        update_markers()

    def _widgets_to_profile_updates(self) -> Dict:
        return {
            "favorite": bool(self.favorite.isChecked()),
            "route": str(self.route.currentText()),
            "volume": float(self.volume.value()) / 100.0,
            "pan": float(self.pan.value()) / 100.0,
            "speed": float(self.speed.value()),
            "pitch_semitones": float(self.pitch.value()),
            "fade_in_ms": int(self.fade_in.value()),
            "fade_out_ms": int(self.fade_out.value()),
            "trim_start_ms": int(self.trim_start.value()),
            "trim_end_ms": int(self.trim_end.value()),
            "loop_start_ms": int(self.loop_start.value()),
            "loop_end_ms": int(self.loop_end.value()),
        }

    def _save(self) -> None:
        updates = self._widgets_to_profile_updates()
        set_profile(self.sound_path, updates)
        self.profile = get_profile(self.sound_path)
        save_settings_to_config()

    def _preview(self) -> None:
        # Save first so preview matches.
        self._save()
        play_sound(self.sound_path, loop=False, stop_others=True, start_ms=None)

    def _on_wave_left_click(self, ms: int) -> None:
        # Left click sets trim start
        self.trim_start.setValue(int(ms))

    def _on_wave_right_click(self, ms: int) -> None:
        # Right click sets trim end
        self.trim_end.setValue(int(ms))

