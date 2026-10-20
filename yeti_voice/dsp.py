from __future__ import annotations

import math
from typing import Any


def db_to_linear(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _num(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def build_filter_chain(s: dict[str, Any]) -> str:
    """Translate a Yeti Voice profile into a validated FFmpeg audio chain."""
    filters: list[str] = ["aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=mono"]

    hp = s["highpass"]
    if hp["enabled"]:
        filters.append(f"highpass=f={int(hp['frequency'])}:p=2")

    nr = s["noise_reduction"]
    if nr["enabled"]:
        filters.append(
            f"afftdn=nr={_num(float(nr['amount']))}:nf={_num(float(nr['floor']))}:tn=1:gs=8"
        )

    gate = s["gate"]
    if gate["enabled"]:
        threshold = db_to_linear(float(gate["threshold_db"]))
        filters.append(
            "agate="
            f"threshold={_num(threshold)}:ratio={_num(float(gate['ratio']))}:"
            f"attack={_num(float(gate['attack_ms']))}:release={_num(float(gate['release_ms']))}:"
            "range=0.02:detection=rms"
        )

    eq = s["eq"]
    if eq["enabled"]:
        for band in ("low", "mid", "high"):
            b = eq[band]
            filters.append(
                f"equalizer=f={int(b['frequency'])}:t=q:w={_num(float(b['q']))}:g={_num(float(b['gain_db']))}"
            )

    deesser = s["deesser"]
    if deesser["enabled"]:
        filters.append(
            f"deesser=i={_num(float(deesser['intensity']))}:m=0.7:f={_num(float(deesser['frequency']))}"
        )

    # FFmpeg has no dedicated de-popper. A focused low-frequency cut models
    # Blue VO!CE's plosive cleanup without imposing another hard high-pass.
    popper = s["de_popper"]
    if popper["enabled"]:
        filters.append(
            f"equalizer=f={int(popper['frequency'])}:t=q:w=1.2:g=-{_num(float(popper['strength_db']))}"
        )

    comp = s["compressor"]
    if comp["enabled"]:
        filters.append(
            "acompressor="
            f"threshold={_num(db_to_linear(float(comp['threshold_db'])))}:"
            f"ratio={_num(float(comp['ratio']))}:attack={_num(float(comp['attack_ms']))}:"
            f"release={_num(float(comp['release_ms']))}:"
            f"makeup={_num(db_to_linear(float(comp['makeup_db'])))}:knee=2.5:detection=rms"
        )

    pitch = s["pitch"]
    if pitch["enabled"] and abs(float(pitch["semitones"])) > 0.01:
        filters.append(f"rubberband=pitch={_num(2.0 ** (float(pitch['semitones']) / 12.0))}:formant=preserved")

    flanger = s["flanger"]
    if flanger["enabled"]:
        filters.append(
            f"flanger=delay=3:depth={_num(float(flanger['depth_ms']))}:"
            f"speed={_num(float(flanger['speed_hz']))}:width={int(flanger['mix'])}"
        )

    chorus = s["chorus"]
    if chorus["enabled"]:
        mix = max(1, min(90, int(chorus["mix"]))) / 100.0
        filters.append(
            f"chorus=0.7:{_num(mix)}:40:{_num(mix)}:{_num(float(chorus['speed_hz']))}:"
            f"{_num(float(chorus['depth_ms']))}"
        )

    reverb = s["reverb"]
    if reverb["enabled"]:
        wet = max(0.01, min(0.7, float(reverb["mix"]) / 100.0))
        scale = max(0.2, min(2.0, float(reverb["size"]) / 45.0))
        delays = "|".join(str(int(x * scale)) for x in (29, 43, 71, 103))
        decays = "|".join(_num(wet * x) for x in (1.0, 0.75, 0.5, 0.3))
        filters.append(f"aecho=0.8:0.75:{delays}:{decays}")

    ring = s["ring_mod"]
    if ring["enabled"]:
        filters.append(f"tremolo=f={_num(float(ring['frequency']))}:d={_num(float(ring['depth']))}")

    delay = s["delay"]
    if delay["enabled"]:
        filters.append(
            f"aecho=0.85:0.75:{int(delay['time_ms'])}:{_num(float(delay['feedback']))}"
        )

    limiter = s["limiter"]
    if limiter["enabled"]:
        filters.append(
            f"alimiter=limit={_num(db_to_linear(float(limiter['ceiling_db'])))}:"
            f"attack=5:release={_num(float(limiter['release_ms']))}:level=0"
        )

    if s.get("mute"):
        filters.append("volume=0")
    else:
        filters.append(f"volume={_num(float(s['master_db']))}dB")
    return ",".join(filters)
