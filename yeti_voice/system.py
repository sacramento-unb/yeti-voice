from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


VID = "046d"
PID = "0ab1"


def run(command: list[str], timeout: float = 4.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)


def usb_device() -> dict[str, Any]:
    for path in Path("/sys/bus/usb/devices").glob("*"):
        try:
            if (path / "idVendor").read_text().strip().lower() != VID:
                continue
            if (path / "idProduct").read_text().strip().lower() != PID:
                continue
            return {
                "connected": True,
                "path": path.name,
                "manufacturer": (path / "manufacturer").read_text().strip(),
                "product": (path / "product").read_text().strip(),
                "authorized": (path / "authorized").read_text().strip() == "1",
            }
        except OSError:
            continue
    return {"connected": False}


def alsa_card() -> str | None:
    try:
        text = Path("/proc/asound/cards").read_text()
    except OSError:
        return None
    for line in text.splitlines():
        if "Yeti Nano" in line or "Blue Microphones" in line:
            match = re.match(r"\s*(\d+)\s+\[([^]]+)", line)
            if match:
                return match.group(2).strip()
    return None


def alsa_controls(card: str | None = None) -> list[str]:
    card = card or alsa_card()
    if not card:
        return []
    try:
        result = run(["amixer", "-c", card, "scontrols"], timeout=3)
    except subprocess.TimeoutExpired:
        return []
    return re.findall(r"'([^']+)'", result.stdout)


def _find_control(kind: str) -> tuple[str, str] | None:
    card = alsa_card()
    controls = alsa_controls(card)
    if not card:
        return None
    if kind == "gain":
        candidates = [c for c in controls if "capture" in c.lower() or "mic" in c.lower()]
    else:
        candidates = [
            c
            for c in controls
            if c.lower() == "pcm" or any(x in c.lower() for x in ("speaker", "headphone", "pcm playback"))
        ]
    return (card, candidates[0]) if candidates else None


def set_hardware_percent(kind: str, value: int) -> tuple[bool, str]:
    found = _find_control(kind)
    if not found:
        return False, "controle ALSA indisponível"
    card, control = found
    try:
        result = run(["amixer", "-c", card, "sset", control, f"{max(0, min(100, value))}%"], timeout=3)
    except subprocess.TimeoutExpired:
        return False, "Yeti não respondeu (timeout USB)"
    if result.returncode:
        return False, (result.stderr.strip() or "falha no amixer")
    return True, control


def pulse_json(object_type: str) -> list[dict[str, Any]]:
    result = run(["pactl", "-f", "json", "list", object_type], timeout=4)
    if result.returncode:
        return []
    try:
        value = json.loads(result.stdout)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def find_yeti_source() -> str | None:
    override = os.environ.get("YETI_VOICE_SOURCE")
    if override:
        return override
    for source in pulse_json("sources"):
        name = source.get("name", "")
        props = source.get("properties", {})
        haystack = " ".join(
            str(props.get(k, ""))
            for k in ("device.description", "device.product.name", "device.vendor.name", "node.nick")
        ).lower()
        if "yeti nano" in haystack and not name.endswith(".monitor") and name != "yeti_voice_bus.monitor":
            return name
    return None


def default_source() -> str | None:
    try:
        result = run(["pactl", "get-default-source"], timeout=3)
    except subprocess.TimeoutExpired:
        return None
    value = result.stdout.strip()
    return value or None


def diagnostics() -> dict[str, Any]:
    usb = usb_device()
    card = alsa_card()
    source = None
    pulse_error = ""
    try:
        source = find_yeti_source()
    except subprocess.TimeoutExpired:
        pulse_error = "PipeWire/Pulse bloqueado aguardando o dispositivo USB"
    return {
        "usb": usb,
        "alsa_card": card,
        "alsa_controls": alsa_controls(card),
        "pulse_source": source,
        "pulse_error": pulse_error,
        "healthy": bool(usb.get("connected") and card and source),
        "recommendation": (
            "pronto"
            if usb.get("connected") and card and source
            else "desconecte o Yeti, aguarde 10 s e conecte-o diretamente a uma porta USB (sem o hub)"
        ),
    }
