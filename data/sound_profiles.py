from __future__ import annotations

import os
from typing import Any, Dict, Optional

from data.app_context import ctx


def normalize_sound_key(path: str) -> str:
    """
    Normalize a sound path for stable dict lookup on Windows.
    We store keys as `normpath(lower(path))`.
    """
    try:
        p = os.path.normpath(path)
    except Exception:
        p = str(path)
    return p.lower()


def default_profile() -> Dict[str, Any]:
    # Keep this minimal + forward-compatible.
    return {
        "favorite": False,
        "route": "both",  # local|virtual|both
        "volume": 1.0,  # 0..1
        "pan": 0.0,  # -1..1 (left..right) (best-effort)
        "speed": 1.0,  # playback rate multiplier (simple resample)
        "pitch_semitones": 0.0,  # simple resample-based pitch (also changes duration)
        "fade_in_ms": 0,
        "fade_out_ms": 0,
        "trim_start_ms": 0,
        "trim_end_ms": 0,  # 0 = no end trim
        "loop_start_ms": 0,
        "loop_end_ms": 0,  # 0 = no loop end
        "last_played_ts": 0.0,
    }


def get_profile(sound_path: str) -> Dict[str, Any]:
    key = normalize_sound_key(sound_path)
    prof = ctx.sound_profiles.get(key)
    if not isinstance(prof, dict):
        prof = {}
    merged = default_profile()
    merged.update(prof)
    return merged


def set_profile(sound_path: str, profile_updates: Dict[str, Any]) -> None:
    key = normalize_sound_key(sound_path)
    prof = get_profile(sound_path)
    prof.update(profile_updates)
    ctx.sound_profiles[key] = prof


def is_favorite(sound_path: str) -> bool:
    return bool(get_profile(sound_path).get("favorite", False))


def toggle_favorite(sound_path: str, value: Optional[bool] = None) -> bool:
    prof = get_profile(sound_path)
    if value is None:
        value = not bool(prof.get("favorite", False))
    set_profile(sound_path, {"favorite": bool(value)})
    return bool(value)

