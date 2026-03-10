from __future__ import annotations

import logging
import os
import re
from difflib import SequenceMatcher
from typing import Dict, Iterable, Optional

from data.app_context import ctx

logger = logging.getLogger("sundpood.windows_audio")

_ROLES_BY_NAME = {
    "console": "eConsole",
    "multimedia": "eMultimedia",
    "communications": "eCommunications",
}
_quit_hook_installed = False
_last_availability_error: Optional[str] = None


def _load_pycaw():
    global _last_availability_error
    if os.name != "nt":
        _last_availability_error = "Windows default-mic switching is only supported on Windows."
        raise RuntimeError(_last_availability_error)

    try:
        import comtypes  # noqa: F401
        import psutil  # noqa: F401
        from pycaw.constants import DEVICE_STATE, EDataFlow, ERole
        from pycaw.pycaw import AudioUtilities
    except ImportError as exc:
        _last_availability_error = (
            "Windows default-mic switching requires pycaw, comtypes, and psutil "
            f"in the current Python environment. Original error: {exc}"
        )
        raise RuntimeError(_last_availability_error) from exc
    except Exception as exc:
        _last_availability_error = f"Windows default-mic switching failed to initialize: {exc}"
        raise RuntimeError(_last_availability_error) from exc

    _last_availability_error = None
    return AudioUtilities, DEVICE_STATE, EDataFlow, ERole


def is_available() -> bool:
    try:
        _load_pycaw()
    except Exception:
        return False
    return True


def get_availability_error() -> str:
    try:
        _load_pycaw()
    except Exception as exc:
        return str(exc)
    return "Windows mic auto-switch is available."


def _normalize_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def _replace_word(text: str, old: str, new: str) -> str:
    pattern = re.compile(re.escape(old), re.IGNORECASE)
    return pattern.sub(new, text)


def _candidate_capture_names(render_name: str) -> list[str]:
    render_name = str(render_name or "").strip()
    if not render_name:
        return []

    candidates = [render_name]
    swaps = [
        ("CABLE Input", "CABLE Output"),
        ("Input", "Output"),
        ("Playback", "Recording"),
        ("Speakers", "Microphone"),
    ]

    for old, new in swaps:
        if re.search(re.escape(old), render_name, re.IGNORECASE):
            candidates.append(_replace_word(render_name, old, new))

    unique: list[str] = []
    seen = set()
    for candidate in candidates:
        key = _normalize_name(candidate)
        if key and key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _iter_active_capture_devices() -> Iterable[object]:
    AudioUtilities, DEVICE_STATE, EDataFlow, _ = _load_pycaw()
    return AudioUtilities.GetAllDevices(
        data_flow=EDataFlow.eCapture.value,
        device_state=DEVICE_STATE.ACTIVE.value,
    )


def _get_capture_device_by_id(device_id: str):
    for device in _iter_active_capture_devices():
        if getattr(device, "id", None) == device_id:
            return device
    return None


def _score_capture_device(device_name: str, candidates: Iterable[str]) -> float:
    device_norm = _normalize_name(device_name)
    if not device_norm:
        return 0.0

    best = 0.0
    device_tokens = set(device_norm.split())
    for candidate in candidates:
        candidate_norm = _normalize_name(candidate)
        if not candidate_norm:
            continue
        if candidate_norm == device_norm:
            return 1.0

        ratio = SequenceMatcher(None, candidate_norm, device_norm).ratio()
        cand_tokens = set(candidate_norm.split())
        token_overlap = len(device_tokens & cand_tokens) / max(1, len(cand_tokens))

        vendor_bonus = 0.0
        for vendor in ("vb", "audio", "cable", "voicemeeter", "virtual"):
            if vendor in device_tokens and vendor in cand_tokens:
                vendor_bonus += 0.03

        best = max(best, ratio * 0.65 + token_overlap * 0.35 + vendor_bonus)
    return best


def resolve_capture_device_for_virtual_output(render_name: Optional[str] = None):
    combo = getattr(getattr(ctx, "pref", None), "virtual_mic_combo", None)
    if render_name is None and combo is not None:
        render_name = combo.currentText()
    if render_name is None:
        render_name = ctx.sound_settings.get("last_virtual_render_name", "")
    render_name = str(render_name or "").strip()
    if not render_name:
        return None

    candidates = _candidate_capture_names(render_name)
    devices = list(_iter_active_capture_devices())

    for candidate in candidates:
        candidate_norm = _normalize_name(candidate)
        for device in devices:
            if _normalize_name(getattr(device, "FriendlyName", "")) == candidate_norm:
                return device

    best_device = None
    best_score = 0.0
    for device in devices:
        score = _score_capture_device(getattr(device, "FriendlyName", ""), candidates)
        if score > best_score:
            best_score = score
            best_device = device

    if best_score >= 0.72:
        return best_device
    return None


def _default_capture_device_for_role(role) -> Optional[object]:
    AudioUtilities, _, EDataFlow, _ = _load_pycaw()
    enumerator = AudioUtilities.GetDeviceEnumerator()
    device = enumerator.GetDefaultAudioEndpoint(EDataFlow.eCapture.value, role.value)
    return AudioUtilities.CreateDevice(device)


def _capture_current_defaults() -> Dict[str, str]:
    _, _, _, ERole = _load_pycaw()
    defaults: Dict[str, str] = {}
    for key, role in (
        ("console", ERole.eConsole),
        ("multimedia", ERole.eMultimedia),
        ("communications", ERole.eCommunications),
    ):
        device = _default_capture_device_for_role(role)
        if device and getattr(device, "id", None):
            defaults[key] = device.id
    return defaults


def describe_saved_defaults() -> Dict[str, str]:
    descriptions: Dict[str, str] = {}
    for role_name, device_id in (ctx.windows_capture_restore_ids or {}).items():
        device = _get_capture_device_by_id(device_id)
        descriptions[role_name] = (
            getattr(device, "FriendlyName", None) or str(device_id)
        )
    return descriptions


def _set_default_capture_device(device_id: str, role_names: Iterable[str]) -> None:
    AudioUtilities, _, _, ERole = _load_pycaw()
    roles = []
    for role_name in role_names:
        role_attr = _ROLES_BY_NAME.get(role_name)
        if role_attr:
            roles.append(getattr(ERole, role_attr))
    if not roles:
        return
    AudioUtilities.SetDefaultDevice(device_id, roles=roles)


def switch_default_recording_to_virtual(render_name: Optional[str] = None) -> tuple[bool, str]:
    target = resolve_capture_device_for_virtual_output(render_name)
    if not target:
        render_name = str(render_name or "").strip() or ctx.sound_settings.get("last_virtual_render_name", "")
        return (
            False,
            f"Could not match a recording device for virtual output '{render_name}'.",
        )

    target_id = getattr(target, "id", None)
    target_name = getattr(target, "FriendlyName", None) or str(target_id)
    if not target_id:
        return (False, "The matched recording device does not expose a Windows endpoint ID.")

    if ctx.windows_capture_switch_active and ctx.windows_capture_target_id == target_id:
        return (True, target_name)

    previous_defaults = (
        dict(ctx.windows_capture_restore_ids)
        if ctx.windows_capture_switch_active and ctx.windows_capture_restore_ids
        else _capture_current_defaults()
    )
    try:
        _set_default_capture_device(
            target_id,
            ("console", "multimedia", "communications"),
        )
    except Exception as exc:
        logger.warning("Failed to switch Windows capture defaults: %s", exc)
        return (False, str(exc))

    ctx.windows_capture_restore_ids = previous_defaults
    ctx.windows_capture_target_id = target_id
    ctx.windows_capture_target_name = target_name
    ctx.windows_capture_switch_active = True
    logger.info("Switched Windows capture defaults to %s", target_name)
    return (True, target_name)


def restore_default_recording() -> tuple[bool, str]:
    restore_ids = dict(ctx.windows_capture_restore_ids or {})
    if not ctx.windows_capture_switch_active or not restore_ids:
        return (True, "No Windows capture device restore was pending.")

    roles_by_device: Dict[str, list[str]] = {}
    for role_name, device_id in restore_ids.items():
        if device_id:
            roles_by_device.setdefault(device_id, []).append(role_name)

    try:
        for device_id, role_names in roles_by_device.items():
            _set_default_capture_device(device_id, role_names)
    except Exception as exc:
        logger.warning("Failed to restore Windows capture defaults: %s", exc)
        return (False, str(exc))

    restored_names = ", ".join(f"{role}: {name}" for role, name in describe_saved_defaults().items())
    ctx.windows_capture_restore_ids = {}
    ctx.windows_capture_target_id = None
    ctx.windows_capture_target_name = None
    ctx.windows_capture_switch_active = False
    logger.info("Restored Windows capture defaults: %s", restored_names)
    return (True, restored_names or "Restored previous Windows capture defaults.")


def sync_windows_recording_defaults(*, notify_user: bool = False) -> tuple[bool, str]:
    autoswitch_enabled = bool(ctx.sound_settings.get("auto_switch_windows_mic", False))
    virtual_enabled = bool(ctx.sound_settings.get("virtual_mic_enabled", False))

    if not autoswitch_enabled or not virtual_enabled:
        ok, message = restore_default_recording()
        return (ok, message)

    try:
        ok, message = switch_default_recording_to_virtual(
            getattr(getattr(ctx, "pref", None), "virtual_mic_combo", None).currentText()
            if getattr(getattr(ctx, "pref", None), "virtual_mic_combo", None)
            else None
        )
    except Exception as exc:
        ok, message = False, str(exc)

    if notify_user and not ok:
        logger.warning("Windows mic auto-switch unavailable: %s", message)
    return (ok, message)


def install_quit_restore_hook() -> None:
    global _quit_hook_installed
    if _quit_hook_installed:
        return
    _quit_hook_installed = True

    import atexit
    import signal

    def _restore_on_quit():
        try:
            restore_default_recording()
        except Exception as exc:
            logger.warning("Failed to restore Windows capture defaults during quit: %s", exc)

    atexit.register(_restore_on_quit)

    if getattr(ctx, "app", None) is not None:
        ctx.app.aboutToQuit.connect(_restore_on_quit)

    def _signal_handler(signum, frame):
        _restore_on_quit()
        raise SystemExit(0)

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _signal_handler)
        except (OSError, ValueError):
            pass
