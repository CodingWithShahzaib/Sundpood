"""
Shared application context.

This module exists so we can split the old monolithic `data/main.py` into
smaller files without relying on cross-module globals like `win`, `pref`, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AppContext:
    # Qt objects (set during startup)
    app: Any = None
    win: Any = None
    pref: Any = None
    over: Any = None
    hotk: Any = None
    tray: Any = None
    tray_quitting: bool = False

    # App config
    VERSION: int = 102
    dir_: str = "sounds"
    config_path: str = "settings.json"
    config_loaded: bool = False

    # Loaded state
    theme: str = "None"
    menu: List[Any] = field(default_factory=list)
    select: List[int] = field(default_factory=lambda: [0, 0])
    hotkeys: Dict[str, str] = field(default_factory=dict)

    # Sound settings (persisted in config)
    sound_settings: Dict[str, Any] = field(
        default_factory=lambda: {
            "allow_overlap": True,
            "loop_sounds": False,
            "mic_monitor": False,
            "mic_monitor_volume": 0.7,
            "virtual_mic_enabled": False,
            "mic_passthrough_enabled": False,
            "stop_same_hotkey": False,
            "auto_switch_windows_mic": False,
        }
    )

    # UI settings (persisted in config)
    ui_settings: Dict[str, Any] = field(
        default_factory=lambda: {
            "grid_card_size": 200,  # base icon size (px)
            "grid_padding": 20,  # extra space around card for grid size (px)
            "grid_spacing": 15,  # list spacing (px)
            "grid_sort": "name",  # name|ext|hotkey|recent|none
            "favorites_first": True,
            "enhanced_overlay": True,
            "tray_enabled": True,
        }
    )

    # Per-sound profiles (persisted in config)
    # Key: normalized path key (lowercased normpath)
    sound_profiles: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Runtime tracking
    current_playing_sound: Optional[str] = None
    current_playing_hotkey: Optional[str] = None
    windows_capture_restore_ids: Dict[str, str] = field(default_factory=dict)
    windows_capture_target_id: Optional[str] = None
    windows_capture_target_name: Optional[str] = None
    windows_capture_switch_active: bool = False

    # Keybinding plumbing (populated at startup)
    PREF_BTN: List[Any] = field(default_factory=list)
    COMMAND_DICT: Dict[Any, str] = field(default_factory=dict)  # lambda -> command name
    KEYS_CMD: Dict[Any, str] = field(default_factory=dict)  # lambda -> key string


ctx = AppContext()

