from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .dsp import build_filter_chain
from .model import config_path, load_config, runtime_dir
from .system import default_source, find_yeti_source, run


BUS_NAME = "yeti_voice_bus"
VIRTUAL_SOURCE = f"{BUS_NAME}.monitor"


class Engine:
    def __init__(self) -> None:
        self.running = True
        self.ffmpeg: subprocess.Popen[str] | None = None
        self.module_ids: list[str] = []
        self.previous_default: str | None = None
        self.last_config_stamp: int = -1
        self.last_source: str | None = None
        self.status: dict[str, Any] = {}
        self.runtime = runtime_dir()
        self.runtime.mkdir(parents=True, exist_ok=True)

    def write_status(self, **values: Any) -> None:
        self.status.update(values, updated_at=time.time(), pid=os.getpid())
        target = self.runtime / "status.json"
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.status, indent=2) + "\n")
        os.replace(tmp, target)

    def pulse(self, args: list[str], timeout: float = 4.0) -> subprocess.CompletedProcess[str]:
        return run(["pactl", *args], timeout=timeout)

    def unload_old_bus(self) -> None:
        try:
            result = self.pulse(["list", "short", "modules"])
        except subprocess.TimeoutExpired:
            return
        for line in result.stdout.splitlines():
            if f"sink_name={BUS_NAME}" in line:
                module_id = line.split("\t", 1)[0]
                self.pulse(["unload-module", module_id])

    def ensure_bus(self) -> bool:
        self.unload_old_bus()
        try:
            result = self.pulse(
                [
                    "load-module",
                    "module-null-sink",
                    f"sink_name={BUS_NAME}",
                    "sink_properties=device.description=Yeti_Voice_Bus",
                    "rate=48000",
                    "channels=1",
                    "channel_map=mono",
                ]
            )
        except subprocess.TimeoutExpired:
            self.write_status(state="error", error="PipeWire/Pulse não respondeu")
            return False
        if result.returncode:
            self.write_status(state="error", error=result.stderr.strip() or "falha ao criar fonte virtual")
            return False
        module_id = result.stdout.strip()
        self.module_ids = [module_id] if module_id else []
        self.pulse(["update-source-proplist", VIRTUAL_SOURCE, "device.description=Yeti Voice (Blue VO!CE)"])
        return True

    def stop_ffmpeg(self) -> None:
        if self.ffmpeg and self.ffmpeg.poll() is None:
            self.ffmpeg.terminate()
            try:
                self.ffmpeg.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.ffmpeg.kill()
        self.ffmpeg = None

    def start_pipeline(self, settings: dict[str, Any], source: str) -> bool:
        self.stop_ffmpeg()
        chain = build_filter_chain(settings)
        command = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "warning",
            "-thread_queue_size", "1024", "-f", "pulse", "-sample_rate", "48000",
            "-channels", "1", "-i", source, "-af", chain, "-ar", "48000", "-ac", "1",
            "-f", "pulse", BUS_NAME,
        ]
        log_path = self.runtime / "ffmpeg.log"
        log = log_path.open("a")
        self.ffmpeg = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, text=True)
        time.sleep(0.25)
        if self.ffmpeg.poll() is not None:
            self.write_status(state="error", error=f"FFmpeg encerrou; consulte {log_path}", source=source)
            return False
        if settings.get("set_default_source"):
            if not self.previous_default:
                self.previous_default = default_source()
            self.pulse(["set-default-source", VIRTUAL_SOURCE])
        else:
            self.restore_default()
        self.last_source = source
        self.write_status(state="running", error="", source=source, virtual_source=VIRTUAL_SOURCE, chain=chain)
        return True

    def restore_default(self) -> None:
        if self.previous_default and self.previous_default != VIRTUAL_SOURCE:
            try:
                self.pulse(["set-default-source", self.previous_default])
            except (subprocess.TimeoutExpired, OSError):
                pass

    def cleanup(self) -> None:
        self.stop_ffmpeg()
        self.restore_default()
        for module_id in self.module_ids:
            try:
                self.pulse(["unload-module", module_id])
            except (subprocess.TimeoutExpired, OSError):
                pass
        self.write_status(state="stopped", error="")

    def loop(self) -> int:
        self.write_status(state="starting", error="")
        bus_ready = False
        retry_at = 0.0
        while self.running:
            settings = load_config()
            try:
                stamp = config_path().stat().st_mtime_ns
            except OSError:
                stamp = 0

            if not settings.get("enabled"):
                self.stop_ffmpeg()
                self.restore_default()
                self.write_status(state="disabled", error="")
                time.sleep(0.5)
                continue

            if time.monotonic() < retry_at:
                time.sleep(0.25)
                continue

            try:
                source = find_yeti_source()
            except subprocess.TimeoutExpired:
                source = None
                self.write_status(state="device_error", error="PipeWire travou aguardando o Yeti (timeout USB)")
            if not source:
                self.stop_ffmpeg()
                self.restore_default()
                self.write_status(state="waiting_device", error="Yeti Nano não disponível no PipeWire")
                retry_at = time.monotonic() + 2.0
                continue

            if not bus_ready:
                bus_ready = self.ensure_bus()
                if not bus_ready:
                    retry_at = time.monotonic() + 2.0
                    continue

            died = self.ffmpeg is not None and self.ffmpeg.poll() is not None
            changed = stamp != self.last_config_stamp or source != self.last_source
            if self.ffmpeg is None or died or changed:
                if self.start_pipeline(settings, source):
                    self.last_config_stamp = stamp
                else:
                    retry_at = time.monotonic() + 2.0
            time.sleep(0.25)
        self.cleanup()
        return 0


def main() -> int:
    engine = Engine()

    def stop(_signum: int, _frame: object) -> None:
        engine.running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    return engine.loop()


if __name__ == "__main__":
    sys.exit(main())
