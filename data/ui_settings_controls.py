from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from data.app_context import ctx
from data.config_io import save_settings_to_config
from data.ui_actions import cat_select
from data.windows_audio import get_availability_error, is_available


def inject_grid_settings_controls() -> None:
    """
    Add extra settings groups to the Preferences Settings tab using the
    layout host created by the new ui_preferences.py.
    """
    layout = getattr(ctx.pref, "settings_extra_layout", None)
    if layout is None or hasattr(ctx.pref, "windows_mic_autoswitch_checkbox"):
        return

    routing_group = QtWidgets.QGroupBox("Audio routing")
    routing_layout = QtWidgets.QVBoxLayout(routing_group)
    routing_layout.setContentsMargins(12, 10, 12, 12)
    routing_layout.setSpacing(6)

    autoswitch_checkbox = QtWidgets.QCheckBox(
        "Switch Windows Default and Communications mic to the\n"
        "selected virtual cable while SundPood is running"
    )
    autoswitch_checkbox.setChecked(bool(ctx.sound_settings.get("auto_switch_windows_mic", False)))

    routing_help = QtWidgets.QLabel(
        "Use this when Discord input is set to 'Default'. SundPood\n"
        "restores your previous Windows mic when the app exits normally."
    )
    routing_help.setWordWrap(True)
    if not is_available():
        ctx.sound_settings["auto_switch_windows_mic"] = False
        autoswitch_checkbox.setChecked(False)
        autoswitch_checkbox.setEnabled(False)
        routing_help.setText(
            "Windows mic auto-switch is unavailable.\n"
            f"{get_availability_error()}\n\n"
            "Install pycaw, comtypes, and psutil in the Python\n"
            "environment used to launch SundPood."
        )

    routing_layout.addWidget(autoswitch_checkbox)
    routing_layout.addWidget(routing_help)

    group = QtWidgets.QGroupBox("Sound grid")

    size_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    size_slider.setRange(140, 320)
    size_slider.setValue(int(ctx.ui_settings.get("grid_card_size", 200) or 200))

    spacing_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    spacing_slider.setRange(0, 30)
    spacing_slider.setValue(int(ctx.ui_settings.get("grid_spacing", 15) or 15))

    sort_combo = QtWidgets.QComboBox()
    sort_combo.addItems(["name", "ext", "hotkey", "recent", "none"])
    sort_combo.setCurrentText(str(ctx.ui_settings.get("grid_sort", "name") or "name"))

    fav_first = QtWidgets.QCheckBox("Favorites first")
    fav_first.setChecked(bool(ctx.ui_settings.get("favorites_first", True)))

    info = QtWidgets.QLabel("Changes apply instantly to the current category.")
    info.setWordWrap(True)

    form = QtWidgets.QFormLayout()
    form.addRow("Card size", size_slider)
    form.addRow("Spacing", spacing_slider)
    form.addRow("Sort", sort_combo)
    form.addRow("", fav_first)
    form.addRow("", info)
    group.setLayout(form)

    layout.addWidget(routing_group)
    layout.addWidget(group)
    ctx.pref.windows_mic_autoswitch_checkbox = autoswitch_checkbox

    def apply_changes():
        ctx.ui_settings["grid_card_size"] = int(size_slider.value())
        ctx.ui_settings["grid_spacing"] = int(spacing_slider.value())
        ctx.ui_settings["grid_sort"] = str(sort_combo.currentText())
        ctx.ui_settings["favorites_first"] = bool(fav_first.isChecked())
        save_settings_to_config()
        try:
            cur = ctx.win.catList.currentItem()
            if cur and cur.text():
                cat_select(cur.text())
        except Exception:
            pass

    size_slider.valueChanged.connect(lambda _: apply_changes())
    spacing_slider.valueChanged.connect(lambda _: apply_changes())
    sort_combo.currentTextChanged.connect(lambda _: apply_changes())
    fav_first.stateChanged.connect(lambda _: apply_changes())
