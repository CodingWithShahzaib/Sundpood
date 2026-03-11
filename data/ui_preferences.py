# -*- coding: utf-8 -*-
# Preferences window – built with layouts (no setGeometry).
# Widget object names are kept identical to the originals so that
# app_wiring.py, ui_actions.py, etc. keep working without changes.

from PyQt5 import QtCore, QtGui, QtWidgets

from data.path_utils import resource_path


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(660, 960)
        MainWindow.setMinimumSize(QtCore.QSize(500, 600))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(resource_path("icon.ico")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        MainWindow.setWindowIcon(icon)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        # ── Title bar ──
        self.background = QtWidgets.QWidget()
        self.background.setFixedHeight(45)
        self.background.setObjectName("background")

        self.title = QtWidgets.QLabel("Settings")
        self.title.setObjectName("title")
        self.title.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        font = QtGui.QFont("Segoe UI", 16)
        font.setBold(True)
        self.title.setFont(font)

        self.exit_button = QtWidgets.QPushButton("✕")
        self.exit_button.setObjectName("exit_button")
        self.exit_button.setFixedSize(35, 30)
        self.exit_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.min_button = QtWidgets.QPushButton("−")
        self.min_button.setObjectName("min_button")
        self.min_button.setFixedSize(35, 30)
        self.min_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        title_row = QtWidgets.QHBoxLayout(self.background)
        title_row.setContentsMargins(20, 0, 10, 0)
        title_row.setSpacing(8)
        title_row.addWidget(self.title, 1)
        title_row.addWidget(self.min_button)
        title_row.addWidget(self.exit_button)

        # ── Tab widget ──
        self.tabWidget = QtWidgets.QTabWidget()
        self.tabWidget.setObjectName("tabWidget")
        self.tabWidget.setUsesScrollButtons(True)
        self.tabWidget.tabBar().setExpanding(False)
        self.tabWidget.tabBar().setElideMode(QtCore.Qt.ElideRight)

        # ── Root layout ──
        root = QtWidgets.QVBoxLayout(self.centralwidget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.background)

        tab_wrapper = QtWidgets.QVBoxLayout()
        tab_wrapper.setContentsMargins(15, 10, 15, 15)
        tab_wrapper.addWidget(self.tabWidget, 1)
        root.addLayout(tab_wrapper, 1)

        MainWindow.setCentralWidget(self.centralwidget)

        # ── Build every tab ──
        self._build_audio_tab()
        self._build_settings_tab()
        self._build_themes_tab()
        self._build_hotkeys_tab()

        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    # ------------------------------------------------------------------ Audio
    def _build_audio_tab(self):
        self.audio_tab = QtWidgets.QWidget()
        self.audio_tab.setObjectName("audio_tab")

        self.audio_instructions = QtWidgets.QLabel(
            "📖 Quick Setup: Select your headphones below, then select Virtual Cable for Discord/Game. "
            "Enable the checkboxes to route sounds and your microphone to the virtual device."
        )
        self.audio_instructions.setWordWrap(True)
        self.audio_instructions.setObjectName("audio_instructions")

        self.output_section_label = self._section_label("OUTPUT DEVICES", "output_section_label")
        self.headphones_label = self._hint_label("🎧 Your Headphones (You hear sounds here)", "headphones_label")
        self.output_device_combo = QtWidgets.QComboBox()
        self.output_device_combo.setObjectName("output_device_combo")

        self.virtual_cable_label = self._hint_label("🎙️ Virtual Cable (Discord/Game hears from here)", "virtual_cable_label")
        self.virtual_mic_combo = QtWidgets.QComboBox()
        self.virtual_mic_combo.setObjectName("virtual_mic_combo")
        self.virtual_mic_checkbox = QtWidgets.QCheckBox("✓ Send sounds to Virtual Cable")
        self.virtual_mic_checkbox.setObjectName("virtual_mic_checkbox")

        self.input_section_label = self._section_label("INPUT DEVICE", "input_section_label")
        self.input_device_label = self._hint_label("🎤 Your Microphone", "input_device_label")
        self.input_device_combo = QtWidgets.QComboBox()
        self.input_device_combo.setObjectName("input_device_combo")
        self.passthrough_mic_checkbox = QtWidgets.QCheckBox("✓ Route microphone to Virtual Cable")
        self.passthrough_mic_checkbox.setObjectName("passthrough_mic_checkbox")

        btn_row = QtWidgets.QHBoxLayout()
        self.test_output_button = QtWidgets.QPushButton("🔊 Test Headphones")
        self.test_output_button.setObjectName("test_output_button")
        self.test_virtual_button = QtWidgets.QPushButton("🎤 Test Virtual")
        self.test_virtual_button.setObjectName("test_virtual_button")
        btn_row.addWidget(self.test_output_button)
        btn_row.addWidget(self.test_virtual_button)

        self.setup_guide_button = QtWidgets.QPushButton("📘 Full Setup Guide")
        self.setup_guide_button.setObjectName("setup_guide_button")
        self.refresh_devices_button = QtWidgets.QPushButton("🔄 Refresh Devices")
        self.refresh_devices_button.setObjectName("refresh_devices_button")

        body = QtWidgets.QVBoxLayout()
        body.setContentsMargins(15, 15, 15, 15)
        body.setSpacing(6)
        for w in (
            self.audio_instructions,
            self.output_section_label,
            self.headphones_label,
            self.output_device_combo,
            self.virtual_cable_label,
            self.virtual_mic_combo,
            self.virtual_mic_checkbox,
            self.input_section_label,
            self.input_device_label,
            self.input_device_combo,
            self.passthrough_mic_checkbox,
        ):
            body.addWidget(w)
        body.addSpacing(6)
        body.addLayout(btn_row)
        body.addWidget(self.setup_guide_button)
        body.addWidget(self.refresh_devices_button)
        body.addStretch(1)

        scroll = self._scrollable(body)
        tab_lay = QtWidgets.QVBoxLayout(self.audio_tab)
        tab_lay.setContentsMargins(0, 0, 0, 0)
        tab_lay.addWidget(scroll)
        self.tabWidget.addTab(self.audio_tab, "Audio Setup")

    # --------------------------------------------------------------- Settings
    def _build_settings_tab(self):
        self.settings_tab = QtWidgets.QWidget()
        self.settings_tab.setObjectName("settings_tab")

        self.sound_settings_label = self._section_label("🔊 Sound Playback Settings", "sound_settings_label")
        self.allow_overlap_checkbox = QtWidgets.QCheckBox("Allow Multiple Sounds Simultaneously")
        self.allow_overlap_checkbox.setObjectName("allow_overlap_checkbox")
        self.allow_overlap_checkbox.setChecked(True)
        self.loop_sounds_checkbox = QtWidgets.QCheckBox("Loop Sounds")
        self.loop_sounds_checkbox.setObjectName("loop_sounds_checkbox")

        self.stop_all_button = QtWidgets.QPushButton("⏹ Stop All Sounds")
        self.stop_all_button.setObjectName("stop_all_button")
        self.open_sound_folder_button = QtWidgets.QPushButton("📂 Open Sound Folder")
        self.open_sound_folder_button.setObjectName("open_sound_folder_button")
        self.reset_settings_button = QtWidgets.QPushButton("↺ Reset All Settings")
        self.reset_settings_button.setObjectName("reset_settings_button")

        # Overlay controls grid
        overlay_group = QtWidgets.QGroupBox("Overlay control")
        overlay_group.setObjectName("overlay_group")
        grid = QtWidgets.QGridLayout(overlay_group)
        grid.setSpacing(4)
        self._overlay_buttons = {}
        overlay_rows = [
            ("Overlay menu up",    "select_move_up",    1),
            ("Overlay menu down",  "select_move_down",  2),
            ("Overlay menu left",  "select_move_left",  3),
            ("Overlay menu right", "select_move_right", 4),
            ("Overlay play sound", "play_sound",        5),
            ("Overlay stop sound", "stop_sound",        6),
        ]
        for label_text, obj_name, row in overlay_rows:
            lbl = QtWidgets.QLabel(label_text)
            lbl.setObjectName(f"pref_over_el{row}")
            btn = QtWidgets.QPushButton()
            btn.setObjectName(obj_name)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(btn, row, 1)
            setattr(self, f"pref_over_el{row}", lbl)
            setattr(self, obj_name, btn)

        self.pref_over = QtWidgets.QLabel("Overlay control")
        self.pref_over.setObjectName("pref_over")
        self.pref_over.hide()

        # Keep gridLayoutWidget reference for compatibility
        self.gridLayoutWidget = overlay_group
        self.gridLayout = grid

        # Extra settings host (injected at runtime by ui_settings_controls)
        self._settings_extra_host = QtWidgets.QWidget()
        self.settings_extra_layout = QtWidgets.QVBoxLayout(self._settings_extra_host)
        self.settings_extra_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_extra_layout.setSpacing(8)

        body = QtWidgets.QVBoxLayout()
        body.setContentsMargins(15, 15, 15, 15)
        body.setSpacing(8)
        body.addWidget(self.sound_settings_label)
        body.addWidget(self.allow_overlap_checkbox)
        body.addWidget(self.loop_sounds_checkbox)
        body.addWidget(self.stop_all_button)
        body.addWidget(self.open_sound_folder_button)
        body.addWidget(self.reset_settings_button)
        body.addSpacing(4)
        body.addWidget(overlay_group)
        body.addWidget(self._settings_extra_host)
        body.addStretch(1)

        scroll = self._scrollable(body)
        tab_lay = QtWidgets.QVBoxLayout(self.settings_tab)
        tab_lay.setContentsMargins(0, 0, 0, 0)
        tab_lay.addWidget(scroll)
        self.tabWidget.addTab(self.settings_tab, "Settings")

    # ---------------------------------------------------------------- Themes
    def _build_themes_tab(self):
        self.themes_tab = QtWidgets.QWidget()
        self.themes_tab.setObjectName("themes_tab")

        self.pref_themes = self._section_label("🎨 Select Theme", "pref_themes")
        self.themesList = QtWidgets.QListWidget()
        self.themesList.setObjectName("themesList")
        self.update_button = QtWidgets.QPushButton("🔄 Check for Updates")
        self.update_button.setObjectName("update_button")

        lay = QtWidgets.QVBoxLayout(self.themes_tab)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(8)
        lay.addWidget(self.pref_themes)
        lay.addWidget(self.themesList, 1)
        lay.addWidget(self.update_button)
        self.tabWidget.addTab(self.themes_tab, "Themes")

    # --------------------------------------------------------------- Hotkeys
    def _build_hotkeys_tab(self):
        self.hotkeys_tab = QtWidgets.QWidget()
        self.hotkeys_tab.setObjectName("hotkeys_tab")

        search_row = QtWidgets.QHBoxLayout()
        self.hotkey_search_label = QtWidgets.QLabel("Search:")
        self.hotkey_search_label.setObjectName("hotkey_search_label")
        font = QtGui.QFont()
        font.setBold(True)
        self.hotkey_search_label.setFont(font)
        self.hotkey_search = QtWidgets.QLineEdit()
        self.hotkey_search.setObjectName("hotkey_search")
        self.hotkey_search.setPlaceholderText("🔍 Search hotkeys...")
        search_row.addWidget(self.hotkey_search_label)
        search_row.addWidget(self.hotkey_search, 1)

        self.hotkeyList = QtWidgets.QListWidget()
        self.hotkeyList.setObjectName("hotkeyList")
        self.hotkeyList.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        btn_row = QtWidgets.QHBoxLayout()
        self.delete_button = QtWidgets.QPushButton("🗑 Delete Selected")
        self.delete_button.setObjectName("delete_button")
        self.clear_all_button = QtWidgets.QPushButton("🗑 Clear All Hotkeys")
        self.clear_all_button.setObjectName("clear_all_button")
        btn_row.addWidget(self.delete_button)
        btn_row.addWidget(self.clear_all_button)

        lay = QtWidgets.QVBoxLayout(self.hotkeys_tab)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(8)
        lay.addLayout(search_row)
        lay.addWidget(self.hotkeyList, 1)
        lay.addLayout(btn_row)
        self.tabWidget.addTab(self.hotkeys_tab, "Hotkeys")

    # ─────────────────────────────────────── helpers
    @staticmethod
    def _scrollable(inner_layout) -> QtWidgets.QScrollArea:
        content = QtWidgets.QWidget()
        content.setLayout(inner_layout)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _section_label(text: str, name: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setObjectName(name)
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(11)
        lbl.setFont(font)
        return lbl

    @staticmethod
    def _hint_label(text: str, name: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setObjectName(name)
        font = QtGui.QFont()
        font.setPointSize(10)
        lbl.setFont(font)
        return lbl
