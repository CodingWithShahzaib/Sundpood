from __future__ import annotations

import math
import os
from typing import Any, Dict, Tuple

import pygame as pg

from data.app_context import ctx
from data.device_utils import init_mixer
from data.sound_profiles import get_profile


def _require_numpy():
    import numpy as np

    return np


def ensure_mixer_ready() -> None:
    """Ensure pygame mixer is initialized so pygame can decode sounds."""
    if pg.mixer.get_init():
        return
    try:
        from data.config_io import jsonread

        preferred_device = None
        try:
            preferred_device = jsonread(ctx.config_path).get("output_device", None)
        except Exception:
            pass
        init_mixer(preferred_device)
    except Exception:
        init_mixer(None)


def load_sound_array(sound_path: str) -> Tuple[int, "Any"]:
    """
    Decode a sound into a numpy float32 array in range [-1, 1].
    Returns (samplerate, array). Array shape: (n,) for mono, (n,2) for stereo.
    """
    np = _require_numpy()
    ensure_mixer_ready()
    snd = pg.mixer.Sound(sound_path)
    arr = pg.sndarray.array(snd)
    freq, fmt, channels = pg.mixer.get_init()
    # Convert to float32 [-1, 1]
    if arr.dtype != np.float32:
        arr = arr.astype(np.float32) / 32768.0
    # Normalize shape
    if arr.ndim == 2 and arr.shape[1] == 1:
        arr = arr[:, 0]
    return int(freq), arr


def duration_ms(samplerate: int, arr: "Any") -> int:
    n = int(arr.shape[0])
    return int((n / float(samplerate)) * 1000)


def _ms_to_frames(ms: int, samplerate: int) -> int:
    return max(0, int((ms / 1000.0) * samplerate))


def _apply_trim(arr: "Any", samplerate: int, start_ms: int, end_ms: int) -> "Any":
    np = _require_numpy()
    start_f = _ms_to_frames(start_ms, samplerate)
    if end_ms and end_ms > 0:
        end_f = _ms_to_frames(end_ms, samplerate)
        end_f = max(0, min(int(arr.shape[0]), end_f))
    else:
        end_f = int(arr.shape[0])
    start_f = max(0, min(int(arr.shape[0]), start_f))
    if end_f <= start_f:
        return np.zeros((0,) + arr.shape[1:], dtype=np.float32)
    return arr[start_f:end_f]


def _resample(arr: "Any", factor: float) -> "Any":
    """
    Simple resample by linear interpolation. factor > 1 => faster (shorter).
    """
    np = _require_numpy()
    if factor == 1.0:
        return arr
    factor = max(0.25, min(4.0, float(factor)))
    n = int(arr.shape[0])
    if n <= 1:
        return arr
    new_n = max(1, int(n / factor))
    x_old = np.linspace(0.0, 1.0, n, endpoint=False)
    x_new = np.linspace(0.0, 1.0, new_n, endpoint=False)
    if arr.ndim == 1:
        return np.interp(x_new, x_old, arr).astype(np.float32)
    # stereo/multi-channel
    out = np.zeros((new_n, arr.shape[1]), dtype=np.float32)
    for ch in range(arr.shape[1]):
        out[:, ch] = np.interp(x_new, x_old, arr[:, ch]).astype(np.float32)
    return out


def _apply_fade(arr: "Any", samplerate: int, fade_in_ms: int, fade_out_ms: int) -> "Any":
    np = _require_numpy()
    n = int(arr.shape[0])
    if n == 0:
        return arr
    out = arr.copy()
    if fade_in_ms and fade_in_ms > 0:
        f = min(n, _ms_to_frames(fade_in_ms, samplerate))
        if f > 1:
            ramp = np.linspace(0.0, 1.0, f, endpoint=True, dtype=np.float32)
            if out.ndim == 1:
                out[:f] *= ramp
            else:
                out[:f, :] *= ramp[:, None]
    if fade_out_ms and fade_out_ms > 0:
        f = min(n, _ms_to_frames(fade_out_ms, samplerate))
        if f > 1:
            ramp = np.linspace(1.0, 0.0, f, endpoint=True, dtype=np.float32)
            if out.ndim == 1:
                out[n - f :] *= ramp
            else:
                out[n - f :, :] *= ramp[:, None]
    return out


def _apply_pan_and_volume(arr: "Any", volume: float, pan: float) -> "Any":
    np = _require_numpy()
    out = arr.copy()
    volume = float(volume)
    pan = max(-1.0, min(1.0, float(pan)))
    if out.ndim == 1:
        out *= volume
        return out
    # stereo-ish: scale channels
    left = 1.0 - max(0.0, pan)
    right = 1.0 + min(0.0, pan)
    out[:, 0] *= left * volume
    if out.shape[1] > 1:
        out[:, 1] *= right * volume
    # Optional: if more channels, just apply volume
    if out.shape[1] > 2:
        out[:, 2:] *= volume
    return out


def process_sound(
    sound_path: str,
    start_ms_override: int | None = None,
    *,
    use_loop_region: bool = False,
) -> Tuple[int, "Any", Dict[str, Any]]:
    """
    Apply per-sound profile processing.
    Returns (samplerate, processed_array, profile_used).
    """
    np = _require_numpy()
    samplerate, arr = load_sound_array(sound_path)
    prof = get_profile(sound_path)
    source_arr = arr

    trim_start = int(prof.get("trim_start_ms", 0) or 0)
    if start_ms_override is not None:
        trim_start = max(0, int(start_ms_override))
    trim_end = int(prof.get("trim_end_ms", 0) or 0)

    arr = _apply_trim(arr, samplerate, trim_start, trim_end)

    # Loop markers should only affect playback when looping is enabled.
    loop_start = int(prof.get("loop_start_ms", 0) or 0)
    loop_end = int(prof.get("loop_end_ms", 0) or 0)
    if use_loop_region and loop_end and loop_end > loop_start:
        region = _apply_trim(source_arr, samplerate, loop_start, loop_end)
        if region.shape[0] > 0:
            arr = region

    # Speed + pitch (simple resample based)
    speed = float(prof.get("speed", 1.0) or 1.0)
    pitch_semi = float(prof.get("pitch_semitones", 0.0) or 0.0)
    pitch_factor = math.pow(2.0, pitch_semi / 12.0)
    factor = speed * pitch_factor
    if factor != 1.0:
        arr = _resample(arr, factor)

    # Fade
    fade_in = int(prof.get("fade_in_ms", 0) or 0)
    fade_out = int(prof.get("fade_out_ms", 0) or 0)
    arr = _apply_fade(arr, samplerate, fade_in, fade_out)

    # Pan + volume
    volume = float(prof.get("volume", 1.0) or 1.0)
    pan = float(prof.get("pan", 0.0) or 0.0)
    arr = _apply_pan_and_volume(arr, volume, pan)

    # Clamp
    if arr.size:
        arr = np.clip(arr, -1.0, 1.0, out=arr)

    return samplerate, arr, prof


def float_to_int16(arr: "Any") -> "Any":
    np = _require_numpy()
    if arr.dtype != np.float32:
        arr = arr.astype(np.float32)
    arr = np.clip(arr, -1.0, 1.0)
    return (arr * 32767.0).astype(np.int16)


def waveform_envelope(arr: "Any", points: int = 500) -> list[float]:
    """
    Return `points` peak values (0..1) representing the waveform envelope.
    """
    np = _require_numpy()
    if arr is None:
        return []
    if arr.size == 0:
        return [0.0] * points
    mono = arr
    if arr.ndim == 2 and arr.shape[1] >= 2:
        mono = arr.mean(axis=1)
    mono = np.abs(mono.astype(np.float32))
    n = int(mono.shape[0])
    points = max(50, min(2000, int(points)))
    block = max(1, n // points)
    env = []
    for i in range(points):
        start = i * block
        end = min(n, (i + 1) * block)
        if start >= n:
            env.append(0.0)
        else:
            env.append(float(mono[start:end].max(initial=0.0)))
    # Normalize to 0..1
    m = max(env) if env else 1.0
    if m <= 0:
        return [0.0] * points
    return [min(1.0, v / m) for v in env]

