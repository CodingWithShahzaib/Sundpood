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

    # App config
    VERSION: int = 102
    dir_: str = "sound"
    config_path: str = "settings.json"

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
        }
    )

    # Runtime tracking
    current_playing_sound: Optional[str] = None
    current_playing_hotkey: Optional[str] = None

    # Keybinding plumbing (populated at startup)
    PREF_BTN: List[Any] = field(default_factory=list)
    COMMAND_DICT: Dict[Any, str] = field(default_factory=dict)  # lambda -> command name
    KEYS_CMD: Dict[Any, str] = field(default_factory=dict)  # lambda -> key string


ctx = AppContext()

