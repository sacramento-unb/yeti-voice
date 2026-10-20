from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any


APP_NAME = "yeti-voice"
PROFILE_SCHEMA_VERSION = 1


DEFAULTS: dict[str, Any] = {
    "active_profile": "Natural",
    "profile_modified": False,
    "enabled": True,
    "set_default_source": True,
    "mute": False,
    "hardware_gain": 55,
    "headphone_volume": 60,
    "master_db": 0.0,
    "highpass": {"enabled": True, "frequency": 80},
    "noise_reduction": {"enabled": True, "amount": 12.0, "floor": -55.0},
    "gate": {
        "enabled": True,
        "threshold_db": -48.0,
        "ratio": 3.0,
        "attack_ms": 10.0,
        "release_ms": 180.0,
    },
    "eq": {
        "enabled": True,
        "low": {"frequency": 180, "gain_db": -1.5, "q": 0.8},
        "mid": {"frequency": 900, "gain_db": 1.0, "q": 1.0},
        "high": {"frequency": 4000, "gain_db": 1.5, "q": 0.8},
    },
    "deesser": {"enabled": True, "intensity": 0.35, "frequency": 0.55},
    "de_popper": {"enabled": True, "strength_db": 3.0, "frequency": 120},
    "compressor": {
        "enabled": True,
        "threshold_db": -22.0,
        "ratio": 3.0,
        "attack_ms": 12.0,
        "release_ms": 140.0,
        "makeup_db": 3.0,
    },
    "limiter": {"enabled": True, "ceiling_db": -1.0, "release_ms": 50.0},
    "pitch": {"enabled": False, "semitones": 0.0},
    "flanger": {"enabled": False, "depth_ms": 2.0, "speed_hz": 0.5, "mix": 35},
    "chorus": {"enabled": False, "depth_ms": 2.0, "speed_hz": 0.8, "mix": 20},
    "reverb": {"enabled": False, "mix": 15, "size": 45},
    "ring_mod": {"enabled": False, "frequency": 35.0, "depth": 0.5},
    "delay": {"enabled": False, "time_ms": 180, "feedback": 0.25},
}


BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "Natural": {
        "description": "Som equilibrado e transparente para uso geral.",
        "settings": {},
    },
    "Broadcast": {
        "description": "Voz encorpada e nivelada para lives e locução.",
        "settings": {
        "master_db": 1.5,
        "highpass": {"enabled": True, "frequency": 85},
        "noise_reduction": {"enabled": True, "amount": 14.0, "floor": -55.0},
        "gate": {"enabled": True, "threshold_db": -46.0, "ratio": 3.5},
        "eq": {
            "enabled": True,
            "low": {"gain_db": 1.5},
            "mid": {"gain_db": -0.5},
            "high": {"gain_db": 2.5},
        },
        "compressor": {"enabled": True, "threshold_db": -24.0, "ratio": 3.5, "makeup_db": 4.0},
        },
    },
    "Voz Nítida": {
        "description": "Mais presença e inteligibilidade, com sibilância controlada.",
        "settings": {
        "highpass": {"enabled": True, "frequency": 100},
        "eq": {
            "enabled": True,
            "low": {"gain_db": -2.0},
            "mid": {"frequency": 1800, "gain_db": 1.5},
            "high": {"frequency": 5200, "gain_db": 3.0},
        },
        "deesser": {"enabled": True, "intensity": 0.45},
        "de_popper": {"enabled": True, "strength_db": 2.0},
        },
    },
    "Rádio": {
        "description": "Compressão forte e médios destacados, estilo rádio FM.",
        "settings": {
        "highpass": {"enabled": True, "frequency": 160},
        "eq": {
            "enabled": True,
            "low": {"frequency": 220, "gain_db": 4.0, "q": 0.9},
            "mid": {"frequency": 1100, "gain_db": -2.0, "q": 1.0},
            "high": {"frequency": 3800, "gain_db": 3.5, "q": 0.9},
        },
        "compressor": {"enabled": True, "threshold_db": -28.0, "ratio": 5.0, "makeup_db": 5.0},
        },
    },
    "Podcast": {
        "description": "Voz quente e consistente para gravações longas.",
        "settings": {
            "master_db": 1.0,
            "highpass": {"enabled": True, "frequency": 75},
            "noise_reduction": {"enabled": True, "amount": 10.0, "floor": -58.0},
            "gate": {"enabled": True, "threshold_db": -52.0, "ratio": 2.5, "release_ms": 260.0},
            "eq": {
                "enabled": True,
                "low": {"frequency": 160, "gain_db": 2.0, "q": 0.7},
                "mid": {"frequency": 1200, "gain_db": -1.0, "q": 1.0},
                "high": {"frequency": 4200, "gain_db": 1.0, "q": 0.8},
            },
            "compressor": {"enabled": True, "threshold_db": -23.0, "ratio": 2.5, "makeup_db": 3.0},
        },
    },
    "Streaming": {
        "description": "Gate mais firme para teclado e ventoinhas durante jogos.",
        "settings": {
            "highpass": {"enabled": True, "frequency": 95},
            "noise_reduction": {"enabled": True, "amount": 18.0, "floor": -52.0},
            "gate": {"enabled": True, "threshold_db": -42.0, "ratio": 5.0, "attack_ms": 6.0, "release_ms": 150.0},
            "eq": {
                "enabled": True,
                "low": {"frequency": 180, "gain_db": -1.5},
                "mid": {"frequency": 1600, "gain_db": 1.5},
                "high": {"frequency": 4800, "gain_db": 2.0},
            },
            "compressor": {"enabled": True, "threshold_db": -20.0, "ratio": 4.0, "makeup_db": 3.0},
        },
    },
    "Reunião": {
        "description": "Fala limpa e leve para chamadas e videoconferências.",
        "settings": {
            "master_db": 0.0,
            "highpass": {"enabled": True, "frequency": 110},
            "noise_reduction": {"enabled": True, "amount": 20.0, "floor": -50.0},
            "gate": {"enabled": True, "threshold_db": -45.0, "ratio": 3.0, "release_ms": 220.0},
            "eq": {
                "enabled": True,
                "low": {"gain_db": -2.0},
                "mid": {"frequency": 1900, "gain_db": 2.0},
                "high": {"frequency": 5000, "gain_db": 1.5},
            },
            "compressor": {"enabled": True, "threshold_db": -18.0, "ratio": 2.5, "makeup_db": 2.0},
        },
    },
    "ASMR": {
        "description": "Dinâmica ampla e processamento mínimo para detalhes sutis.",
        "settings": {
            "master_db": -2.0,
            "highpass": {"enabled": True, "frequency": 55},
            "noise_reduction": {"enabled": True, "amount": 5.0, "floor": -65.0},
            "gate": {"enabled": False},
            "deesser": {"enabled": True, "intensity": 0.2},
            "de_popper": {"enabled": True, "strength_db": 1.5},
            "eq": {
                "enabled": True,
                "low": {"frequency": 140, "gain_db": 0.5},
                "mid": {"frequency": 1200, "gain_db": 0.0},
                "high": {"frequency": 6500, "gain_db": 1.5},
            },
            "compressor": {"enabled": True, "threshold_db": -30.0, "ratio": 1.5, "makeup_db": 1.0},
            "limiter": {"enabled": True, "ceiling_db": -2.0},
        },
    },
}

# Compatibility for callers from the initial release.
PRESETS: dict[str, dict[str, Any]] = {
    name: copy.deepcopy(spec["settings"]) for name, spec in BUILTIN_PROFILES.items()
}


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def config_dir() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / APP_NAME


def config_path() -> Path:
    override = os.environ.get("YETI_VOICE_CONFIG")
    return Path(override) if override else config_dir() / "config.json"


def profiles_path() -> Path:
    override = os.environ.get("YETI_VOICE_PROFILES")
    return Path(override) if override else config_path().with_name("profiles.json")


def runtime_dir() -> Path:
    root = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/yeti-voice-{os.getuid()}"))
    return root / APP_NAME


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return copy.deepcopy(DEFAULTS)
    try:
        return deep_merge(DEFAULTS, json.loads(path.read_text()))
    except (OSError, json.JSONDecodeError, TypeError):
        return copy.deepcopy(DEFAULTS)


def save_config(settings: dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def load_user_profiles() -> dict[str, dict[str, Any]]:
    path = profiles_path()
    if not path.exists():
        return {}
    try:
        document = json.loads(path.read_text())
        profiles = document.get("profiles", {})
        if not isinstance(profiles, dict):
            return {}
        return {
            str(name): profile
            for name, profile in profiles.items()
            if isinstance(profile, dict) and isinstance(profile.get("settings"), dict)
        }
    except (OSError, json.JSONDecodeError, TypeError, AttributeError):
        return {}


def save_user_profiles(profiles: dict[str, dict[str, Any]]) -> None:
    _atomic_json(profiles_path(), {"version": PROFILE_SCHEMA_VERSION, "profiles": profiles})


def _valid_profile_name(name: str) -> str:
    cleaned = " ".join(name.strip().split())
    if not cleaned or len(cleaned) > 48 or any(ord(char) < 32 for char in cleaned):
        raise ValueError("nome do perfil deve ter entre 1 e 48 caracteres")
    return cleaned


def resolve_profile_name(name: str) -> tuple[str, bool]:
    query = name.strip().casefold()
    for builtin_name in BUILTIN_PROFILES:
        if builtin_name.casefold() == query:
            return builtin_name, True
    for custom_name in load_user_profiles():
        if custom_name.casefold() == query:
            return custom_name, False
    raise KeyError(name)


def list_profiles(current: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    active = (current or load_config()).get("active_profile", "Natural")
    modified = bool((current or load_config()).get("profile_modified", False))
    result = [
        {
            "name": name,
            "description": spec["description"],
            "builtin": True,
            "active": name == active,
            "modified": name == active and modified,
        }
        for name, spec in BUILTIN_PROFILES.items()
    ]
    result.extend(
        {
            "name": name,
            "description": profile.get("description", "Perfil personalizado"),
            "builtin": False,
            "active": name == active,
            "modified": name == active and modified,
        }
        for name, profile in sorted(load_user_profiles().items(), key=lambda item: item[0].casefold())
    )
    return result


def profile_settings(name: str, current: dict[str, Any] | None = None) -> dict[str, Any]:
    resolved, builtin = resolve_profile_name(name)
    current = current or load_config()
    if builtin:
        result = deep_merge(DEFAULTS, BUILTIN_PROFILES[resolved]["settings"])
        # Factory profiles tune DSP, never surprise the user with an analogue
        # gain or headphone-volume jump.
        for key in ("hardware_gain", "headphone_volume"):
            if key in current:
                result[key] = current[key]
    else:
        stored = load_user_profiles()[resolved]["settings"]
        result = deep_merge(DEFAULTS, stored)
    result["active_profile"] = resolved
    result["profile_modified"] = False
    return result


def apply_profile(name: str, current: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = profile_settings(name, current)
    save_config(settings)
    return settings


def save_profile(name: str, settings: dict[str, Any], description: str = "Perfil personalizado") -> str:
    cleaned = _valid_profile_name(name)
    if any(cleaned.casefold() == builtin.casefold() for builtin in BUILTIN_PROFILES):
        raise ValueError("perfis de fábrica não podem ser sobrescritos")
    profiles = load_user_profiles()
    existing = next((item for item in profiles if item.casefold() == cleaned.casefold()), None)
    if existing and existing != cleaned:
        del profiles[existing]
    stored = deep_merge(DEFAULTS, settings)
    stored["active_profile"] = cleaned
    stored["profile_modified"] = False
    profiles[cleaned] = {"description": description.strip() or "Perfil personalizado", "settings": stored}
    save_user_profiles(profiles)
    return cleaned


def delete_profile(name: str) -> str:
    resolved, builtin = resolve_profile_name(name)
    if builtin:
        raise ValueError("perfis de fábrica não podem ser excluídos")
    profiles = load_user_profiles()
    del profiles[resolved]
    save_user_profiles(profiles)
    current = load_config()
    if str(current.get("active_profile", "")).casefold() == resolved.casefold():
        save_config(profile_settings("Natural", current))
    return resolved


def mark_profile_modified(settings: dict[str, Any]) -> None:
    settings["profile_modified"] = True


def apply_preset(name: str, current: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible, non-persisting alias for apply_profile()."""
    return profile_settings(name, current)
