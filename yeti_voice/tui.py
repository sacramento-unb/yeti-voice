from __future__ import annotations

import curses
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

from .model import (
    BUILTIN_PROFILES,
    DEFAULTS,
    apply_profile,
    delete_profile,
    list_profiles,
    load_config,
    mark_profile_modified,
    runtime_dir,
    save_config,
    save_profile,
)
from .system import diagnostics, set_hardware_percent


@dataclass
class Control:
    label: str
    path: str
    minimum: float = 0
    maximum: float = 1
    step: float = 1
    unit: str = ""
    kind: str = "number"
    hardware: str | None = None


# 1984 Synthwave Color Pair Constants
CP_MAGENTA = 1     # Neon Hot Magenta
CP_CYAN = 2        # Electric Neon Cyan
CP_YELLOW = 3      # Outrun Sunset Amber / Gold
CP_PURPLE = 4      # Synthwave Violet
CP_GREEN = 5       # Laser Mint Green
CP_RED = 6         # Laser Coral / Red
CP_TAB_ACTIVE = 7  # Dark on Neon Magenta (glowing active tab)
CP_ACCENT_CYAN = 8 # Dark on Electric Cyan
CP_GRID = 9        # Dim Grid Gray
CP_ROW_SEL = 10    # Selected row accent
CP_METER_LOW = 11  # Electric Cyan (0-60%)
CP_METER_MID = 12  # Hot Magenta (60-85%)
CP_METER_HIGH = 13 # Sunset Gold / Laser Red (85-100%)
CP_METER_BG = 14   # Dim Grid Gray for unlit meter bars
CP_BORDER = 15     # Synthwave frame border
CP_BADGE_ROM = 16  # Dark on Neon Cyan
CP_BADGE_RAM = 17  # Dark on Neon Magenta


def cp(pair_id: int) -> int:
    try:
        return curses.color_pair(pair_id)
    except curses.error:
        return 0


TABS: list[tuple[str, list[Control]]] = [
    ("Principal", [
        Control("Blue VO!CE", "enabled", kind="bool"),
        Control("Microfone virtual padrão", "set_default_source", kind="bool"),
        Control("Mute", "mute", kind="bool"),
        Control("Ganho do Nano", "hardware_gain", 0, 100, 2, "%", hardware="gain"),
        Control("Volume dos fones", "headphone_volume", 0, 100, 2, "%", hardware="headphone"),
        Control("Saída master", "master_db", -24, 12, 0.5, " dB"),
    ]),
    ("Limpeza", [
        Control("Passa-altas", "highpass.enabled", kind="bool"),
        Control("Frequência HPF", "highpass.frequency", 40, 300, 5, " Hz"),
        Control("Redução de ruído", "noise_reduction.enabled", kind="bool"),
        Control("Intensidade NR", "noise_reduction.amount", 1, 30, 1, " dB"),
        Control("Piso de ruído", "noise_reduction.floor", -80, -25, 1, " dB"),
        Control("Gate/expander", "gate.enabled", kind="bool"),
        Control("Limiar gate", "gate.threshold_db", -70, -15, 1, " dB"),
        Control("Razão gate", "gate.ratio", 1, 10, 0.5, ":1"),
        Control("Ataque gate", "gate.attack_ms", 0.1, 100, 1, " ms"),
        Control("Release gate", "gate.release_ms", 20, 1000, 10, " ms"),
        Control("De-esser", "deesser.enabled", kind="bool"),
        Control("Intensidade de-esser", "deesser.intensity", 0, 1, 0.05),
        Control("Foco de-esser", "deesser.frequency", 0, 1, 0.05),
        Control("De-popper", "de_popper.enabled", kind="bool"),
        Control("Força de-popper", "de_popper.strength_db", 0, 12, 0.5, " dB"),
        Control("Foco de-popper", "de_popper.frequency", 60, 250, 5, " Hz"),
    ]),
    ("EQ", [
        Control("Voice EQ", "eq.enabled", kind="bool"),
        Control("Low frequência", "eq.low.frequency", 60, 500, 10, " Hz"),
        Control("Low ganho", "eq.low.gain_db", -12, 12, 0.5, " dB"),
        Control("Low Q", "eq.low.q", 0.2, 5, 0.1),
        Control("Mid frequência", "eq.mid.frequency", 300, 4000, 50, " Hz"),
        Control("Mid ganho", "eq.mid.gain_db", -12, 12, 0.5, " dB"),
        Control("Mid Q", "eq.mid.q", 0.2, 5, 0.1),
        Control("High frequência", "eq.high.frequency", 1800, 12000, 100, " Hz"),
        Control("High ganho", "eq.high.gain_db", -12, 12, 0.5, " dB"),
        Control("High Q", "eq.high.q", 0.2, 5, 0.1),
    ]),
    ("Dinâmica", [
        Control("Compressor", "compressor.enabled", kind="bool"),
        Control("Limiar compressor", "compressor.threshold_db", -60, -3, 1, " dB"),
        Control("Razão compressor", "compressor.ratio", 1, 20, 0.5, ":1"),
        Control("Ataque compressor", "compressor.attack_ms", 0.1, 200, 1, " ms"),
        Control("Release compressor", "compressor.release_ms", 10, 2000, 10, " ms"),
        Control("Makeup", "compressor.makeup_db", 0, 18, 0.5, " dB"),
        Control("Limiter", "limiter.enabled", kind="bool"),
        Control("Teto limiter", "limiter.ceiling_db", -12, -0.1, 0.5, " dB"),
        Control("Release limiter", "limiter.release_ms", 1, 1000, 10, " ms"),
    ]),
    ("Efeitos", [
        Control("Pitch shifter", "pitch.enabled", kind="bool"),
        Control("Pitch", "pitch.semitones", -12, 12, 0.5, " st"),
        Control("Flanger/phaser", "flanger.enabled", kind="bool"),
        Control("Flanger depth", "flanger.depth_ms", 0, 10, 0.5, " ms"),
        Control("Flanger speed", "flanger.speed_hz", 0.1, 10, 0.1, " Hz"),
        Control("Flanger mix", "flanger.mix", 0, 100, 5, "%"),
        Control("Chorus", "chorus.enabled", kind="bool"),
        Control("Chorus mix", "chorus.mix", 1, 90, 5, "%"),
        Control("Reverb", "reverb.enabled", kind="bool"),
        Control("Reverb mix", "reverb.mix", 1, 60, 2, "%"),
        Control("Tamanho da sala", "reverb.size", 10, 90, 5, "%"),
        Control("Ring modulator", "ring_mod.enabled", kind="bool"),
        Control("Ring frequência", "ring_mod.frequency", 1, 1000, 5, " Hz"),
        Control("Ring depth", "ring_mod.depth", 0, 1, 0.05),
        Control("Time delay", "delay.enabled", kind="bool"),
        Control("Tempo delay", "delay.time_ms", 10, 1000, 10, " ms"),
        Control("Feedback delay", "delay.feedback", 0.01, 0.9, 0.05),
    ]),
]


def get_path(root: dict[str, Any], path: str) -> Any:
    value: Any = root
    for part in path.split("."):
        value = value[part]
    return value


def set_path(root: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    target = root
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value


def read_status() -> dict[str, Any]:
    path = runtime_dir() / "status.json"
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"state": "offline", "error": "engine ainda não iniciou"}


def ensure_daemon() -> None:
    status = read_status()
    if status.get("pid"):
        try:
            os.kill(int(status["pid"]), 0)
            return
        except (OSError, ValueError):
            pass
    service = subprocess.run(["systemctl", "--user", "start", "yeti-voice.service"], capture_output=True)
    if service.returncode == 0:
        return
    subprocess.Popen(
        [sys.executable, "-m", "yeti_voice.daemon"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def format_value(value: Any, control: Control) -> str:
    if control.kind == "bool":
        return "ON" if value else "OFF"
    if isinstance(value, float):
        text = f"{value:.2f}".rstrip("0").rstrip(".")
    else:
        text = str(value)
    return f"{text}{control.unit}"


class App:
    def __init__(self, screen: curses.window) -> None:
        self.screen = screen
        self.settings = load_config()
        self.tab = 0
        self.selected = 0
        self.scroll = 0
        self.message = "P abre banco RAM/ROM • Setas ajustam • Espaço alterna"
        self.last_diag = 0.0
        self.diag: dict[str, Any] = {}
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        screen.keypad(True)
        screen.timeout(250)
        self.init_palette()

    def init_palette(self) -> None:
        try:
            if not curses.has_colors():
                return
            curses.start_color()
            curses.use_default_colors()
            is_256 = getattr(curses, "COLORS", 0) >= 256
        except (curses.error, AttributeError):
            return

        if is_256:
            color_defs = {
                CP_MAGENTA: (201, -1),       # Neon Hot Magenta
                CP_CYAN: (51, -1),           # Electric Neon Cyan
                CP_YELLOW: (220, -1),        # Outrun Sunset Amber
                CP_PURPLE: (141, -1),        # Synthwave Violet
                CP_GREEN: (48, -1),          # Laser Mint Green
                CP_RED: (196, -1),           # Laser Coral Red
                CP_TAB_ACTIVE: (232, 201),   # Dark on Neon Magenta
                CP_ACCENT_CYAN: (232, 51),   # Dark on Electric Cyan
                CP_GRID: (239, -1),          # Dim Grid Gray
                CP_ROW_SEL: (232, 51),       # Dark on Electric Cyan
                CP_METER_LOW: (51, -1),      # Electric Cyan (0-60%)
                CP_METER_MID: (201, -1),     # Hot Magenta (60-85%)
                CP_METER_HIGH: (208, -1),    # Sunset Amber / Red (85-100%)
                CP_METER_BG: (238, -1),      # Dim Grid Gray for unlit bars
                CP_BORDER: (141, -1),        # Synthwave Violet Frame
                CP_BADGE_ROM: (232, 51),     # Dark on Cyan
                CP_BADGE_RAM: (232, 201),    # Dark on Magenta
            }
        else:
            color_defs = {
                CP_MAGENTA: (curses.COLOR_MAGENTA, -1),
                CP_CYAN: (curses.COLOR_CYAN, -1),
                CP_YELLOW: (curses.COLOR_YELLOW, -1),
                CP_PURPLE: (curses.COLOR_BLUE, -1),
                CP_GREEN: (curses.COLOR_GREEN, -1),
                CP_RED: (curses.COLOR_RED, -1),
                CP_TAB_ACTIVE: (curses.COLOR_BLACK, curses.COLOR_MAGENTA),
                CP_ACCENT_CYAN: (curses.COLOR_BLACK, curses.COLOR_CYAN),
                CP_GRID: (curses.COLOR_WHITE, -1),
                CP_ROW_SEL: (curses.COLOR_BLACK, curses.COLOR_CYAN),
                CP_METER_LOW: (curses.COLOR_CYAN, -1),
                CP_METER_MID: (curses.COLOR_MAGENTA, -1),
                CP_METER_HIGH: (curses.COLOR_YELLOW, -1),
                CP_METER_BG: (curses.COLOR_BLACK, -1),
                CP_BORDER: (curses.COLOR_MAGENTA, -1),
                CP_BADGE_ROM: (curses.COLOR_BLACK, curses.COLOR_CYAN),
                CP_BADGE_RAM: (curses.COLOR_BLACK, curses.COLOR_MAGENTA),
            }

        for pair_id, (fg, bg) in color_defs.items():
            try:
                curses.init_pair(pair_id, fg, bg)
            except curses.error:
                pass

    def safe_add(self, y: int, x: int, text: str, attr: int = 0) -> None:
        height, width = self.screen.getmaxyx()
        if 0 <= y < height and x < width:
            try:
                self.screen.addnstr(y, x, text, max(0, width - x - 1), attr)
            except curses.error:
                pass

    def draw_frame_line(
        self,
        y: int,
        left: str,
        mid: str,
        right: str,
        title: str = "",
        title_attr: int = 0,
        border_attr: int = 0,
    ) -> None:
        height, width = self.screen.getmaxyx()
        if y < 0 or y >= height or width < 3:
            return
        inner_len = width - 1 - len(left) - len(right)
        if inner_len <= 0:
            return
        if title:
            title_text = f" {title} "
            if len(title_text) > inner_len:
                title_text = title_text[:inner_len]
            rem = inner_len - len(title_text)
            left_pad = 2
            right_pad = max(0, rem - left_pad)
            self.safe_add(y, 0, left + mid * left_pad, border_attr)
            self.safe_add(y, len(left) + left_pad, title_text, title_attr)
            self.safe_add(y, len(left) + left_pad + len(title_text), mid * right_pad + right, border_attr)
        else:
            self.safe_add(y, 0, left + mid * inner_len + right, border_attr)

    def draw_content_row(self, y: int, border_attr: int = 0) -> None:
        height, width = self.screen.getmaxyx()
        if 0 <= y < height and width >= 3:
            self.safe_add(y, 0, "║", border_attr)
            self.safe_add(y, width - 2, "║", border_attr)

    def draw_meter(
        self,
        y: int,
        x: int,
        value: float,
        minimum: float,
        maximum: float,
        length: int = 14,
        is_selected: bool = False,
    ) -> None:
        if maximum <= minimum:
            ratio = 0.0
        else:
            ratio = max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))

        filled_len = int(round(ratio * length))
        empty_len = length - filled_len

        bracket_attr = cp(CP_PURPLE) if is_selected else cp(CP_GRID)
        self.safe_add(y, x, "[", bracket_attr)
        cur_x = x + 1

        low_cutoff = int(length * 0.60)
        mid_cutoff = int(length * 0.85)

        for i in range(filled_len):
            if i < low_cutoff:
                attr = cp(CP_METER_LOW)
            elif i < mid_cutoff:
                attr = cp(CP_METER_MID)
            else:
                attr = cp(CP_METER_HIGH)
            if is_selected:
                attr |= curses.A_BOLD
            self.safe_add(y, cur_x, "█", attr)
            cur_x += 1

        empty_attr = cp(CP_METER_BG)
        for _ in range(empty_len):
            self.safe_add(y, cur_x, "░", empty_attr)
            cur_x += 1

        self.safe_add(y, cur_x, "]", bracket_attr)

    def adjust(self, direction: int) -> None:
        control = TABS[self.tab][1][self.selected]
        value = get_path(self.settings, control.path)
        if control.kind == "bool":
            value = not value
        else:
            value = max(control.minimum, min(control.maximum, float(value) + direction * control.step))
            if isinstance(get_path(DEFAULTS, control.path), int):
                value = int(round(value))
        set_path(self.settings, control.path, value)
        mark_profile_modified(self.settings)
        save_config(self.settings)
        if control.hardware:
            ok, detail = set_hardware_percent(control.hardware, int(value))
            self.message = ("Hardware: " if ok else "Falha hardware: ") + detail
        else:
            self.message = f"{control.label}: {format_value(value, control)}"

    def apply_named_profile(self, name: str) -> None:
        self.settings = apply_profile(name, self.settings)
        hardware_errors = []
        for kind, key in (("gain", "hardware_gain"), ("headphone", "headphone_volume")):
            ok, _detail = set_hardware_percent(kind, int(self.settings[key]))
            if not ok:
                hardware_errors.append(kind)
        suffix = " • hardware indisponível" if hardware_errors else ""
        self.message = f"Preset aplicado: {self.settings['active_profile']}{suffix}"

    def choose_builtin_profile(self, index: int) -> None:
        names = list(BUILTIN_PROFILES)
        if 0 <= index < len(names):
            self.apply_named_profile(names[index])

    def prompt_text(self, prompt: str, initial: str = "") -> str | None:
        height, width = self.screen.getmaxyx()
        box_y = height - 3
        border_attr = cp(CP_BORDER)
        self.safe_add(box_y, 0, "╠" + "═" * (width - 3) + "╣", border_attr)
        self.safe_add(box_y + 1, 0, "║" + " " * (width - 3) + "║", border_attr)
        self.safe_add(box_y + 1, 2, prompt, cp(CP_YELLOW) | curses.A_BOLD)
        x = min(width - 4, len(prompt) + 3)
        try:
            curses.echo()
            curses.curs_set(1)
            self.screen.timeout(-1)
            self.safe_add(box_y + 1, x, initial, cp(CP_CYAN))
            self.screen.move(box_y + 1, min(width - 4, x + len(initial)))
            raw = self.screen.getstr(box_y + 1, x, max(1, width - x - 4))
            return raw.decode("utf-8", errors="replace").strip() or None
        except curses.error:
            return None
        finally:
            curses.noecho()
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            self.screen.timeout(250)

    def diag_modal(self) -> None:
        self.diag = diagnostics()
        self.message = f"Diagnóstico: {self.diag.get('recommendation')}"
        border_attr = cp(CP_BORDER)

        while True:
            self.screen.erase()
            h, w = self.screen.getmaxyx()
            self.draw_frame_line(
                0, "╔", "═", "╗",
                "⚡ DIAGNÓSTICO DO HARDWARE // TELEMETRIA 1984 ⚡",
                cp(CP_MAGENTA) | curses.A_BOLD,
                border_attr,
            )

            diag = self.diag
            usb = diag.get("usb", {})
            usb_connected = usb.get("connected", False)
            card = diag.get("alsa_card")
            controls = diag.get("alsa_controls", [])
            source = diag.get("pulse_source")
            error = diag.get("pulse_error")
            healthy = diag.get("healthy", False)
            recommendation = diag.get("recommendation", "Sem dados")

            for y in range(1, h - 1):
                self.draw_content_row(y, border_attr)

            self.safe_add(2, 3, "DIAGNÓSTICO DO SISTEMA BLUE VO!CE / YETI NANO", cp(CP_CYAN) | curses.A_BOLD)
            self.safe_add(3, 3, "Varredura de barramento USB, driver ALSA e roteamento PipeWire", cp(CP_PURPLE))

            self.safe_add(5, 3, "ESTADO GERAL     :", cp(CP_PURPLE))
            if healthy:
                self.safe_add(5, 23, "[ ÓTIMO // HEALTHY ● ]", cp(CP_GREEN) | curses.A_BOLD)
            else:
                self.safe_add(5, 23, "[ ATENÇÃO // FALHA ▲ ]", cp(CP_RED) | curses.A_BOLD)

            self.safe_add(7, 3, "DISPOSITIVO USB  :", cp(CP_PURPLE))
            if usb_connected:
                dev_info = f"Conectado ({usb.get('path', 'usb')} • {usb.get('product', 'Yeti Nano')})"
                self.safe_add(7, 23, f"[OK] {dev_info}", cp(CP_CYAN))
            else:
                self.safe_add(7, 23, "[NÃO DETECTADO] Yeti Nano não encontrado no barramento USB", cp(CP_RED) | curses.A_BOLD)

            self.safe_add(8, 3, "PLACA ALSA       :", cp(CP_PURPLE))
            if card:
                ctrls_str = ", ".join(controls) if controls else "Nenhum"
                self.safe_add(8, 23, f"[OK] Placa: {card} (Controles: {ctrls_str})", cp(CP_CYAN))
            else:
                self.safe_add(8, 23, "[AUSENTE] Nenhuma placa ALSA correspondente ao Yeti", cp(CP_RED))

            self.safe_add(9, 3, "FONTE PIPEWIRE   :", cp(CP_PURPLE))
            if source:
                max_src_w = max(10, w - 34)
                src_disp = source if len(source) <= max_src_w else source[:max_src_w - 3] + "..."
                self.safe_add(9, 23, f"[OK] {src_disp}", cp(CP_CYAN))
            else:
                self.safe_add(9, 23, "[OFFLINE] Nenhuma fonte PipeWire detectada", cp(CP_YELLOW))

            if error:
                self.safe_add(10, 3, "ERRO PIPEWIRE    :", cp(CP_RED))
                self.safe_add(10, 23, error, cp(CP_RED) | curses.A_BOLD)

            rec_y = min(12, h - 6)
            self.draw_frame_line(rec_y, "╠", "═", "╣", "RECOMENDAÇÃO DO SISTEMA", cp(CP_YELLOW) | curses.A_BOLD, border_attr)
            self.safe_add(rec_y + 2, 3, f"» {recommendation}", cp(CP_CYAN) | curses.A_BOLD)

            self.draw_frame_line(h - 1, "╚", "═", "╝", "Pressione qualquer tecla ou Esc para voltar ao rack", cp(CP_YELLOW), border_attr)
            self.screen.refresh()

            key = self.screen.getch()
            if key != -1:
                return

    def profile_menu(self) -> None:
        entries = list_profiles(self.settings)
        selected = next((i for i, item in enumerate(entries) if item["active"]), 0)
        scroll = 0
        menu_message = "Enter aplicar • S salvar atual • X excluir personalizado • Esc voltar"
        border_attr = cp(CP_BORDER)

        while True:
            self.screen.erase()
            h, w = self.screen.getmaxyx()

            self.draw_frame_line(
                0, "╔", "═", "╗",
                "◈ BANCO DE PRESETS // CARTRIDGE 1984 ◈",
                cp(CP_MAGENTA) | curses.A_BOLD,
                border_attr,
            )

            self.draw_content_row(1, border_attr)
            if w >= 95:
                sub_banner = "[ROM] PRESETS DE FÁBRICA (PROTEGIDO)   •   [RAM] PRESETS DO USUÁRIO (GRAVA HARDWARE E EFEITOS)"
            else:
                sub_banner = "[ROM] FÁBRICA (PROTEGIDO)   •   [RAM] USUÁRIO (GRAVA HARDWARE E EFEITOS)"
            self.safe_add(1, 2, sub_banner[:w - 5], cp(CP_PURPLE))

            self.draw_frame_line(2, "╠", "═", "╣", "SLOTS DE MEMÓRIA", cp(CP_CYAN) | curses.A_BOLD, border_attr)

            top = 3
            visible = max(1, h - 7)
            if selected < scroll:
                scroll = selected
            if selected >= scroll + visible:
                scroll = selected - visible + 1

            for row, index in enumerate(range(scroll, min(len(entries), scroll + visible))):
                curr_y = top + row
                self.draw_content_row(curr_y, border_attr)
                item = entries[index]
                is_selected = (index == selected)

                if is_selected:
                    self.safe_add(curr_y, 2, "►►", cp(CP_YELLOW) | curses.A_BOLD)
                else:
                    self.safe_add(curr_y, 2, "  ", 0)

                active_str = "★" if item["active"] else " "
                mod_str = "*" if item["modified"] else " "
                self.safe_add(curr_y, 5, active_str, cp(CP_YELLOW) | curses.A_BOLD)
                self.safe_add(curr_y, 6, mod_str, cp(CP_MAGENTA) | curses.A_BOLD)

                if item["builtin"]:
                    self.safe_add(curr_y, 8, "[ROM]", cp(CP_BADGE_ROM) | curses.A_BOLD)
                else:
                    self.safe_add(curr_y, 8, "[RAM]", cp(CP_BADGE_RAM) | curses.A_BOLD)

                name_attr = (cp(CP_YELLOW) | curses.A_BOLD) if is_selected else cp(CP_CYAN)
                self.safe_add(curr_y, 14, f"{item['name']:<16}", name_attr)

                desc_w = max(10, w - 36)
                desc = item["description"]
                if len(desc) > desc_w:
                    desc = desc[:desc_w - 1] + "…"
                desc_attr = cp(CP_CYAN) if is_selected else cp(CP_PURPLE)
                self.safe_add(curr_y, 32, desc, desc_attr)

            rendered_rows = min(len(entries), scroll + visible) - scroll
            for empty_row in range(rendered_rows, visible):
                self.draw_content_row(top + empty_row, border_attr)

            self.draw_frame_line(h - 4, "╠", "═", "╣", border_attr=border_attr)

            self.draw_content_row(h - 3, border_attr)
            self.safe_add(h - 3, 2, "⚡ STATUS:", cp(CP_MAGENTA) | curses.A_BOLD)
            self.safe_add(h - 3, 12, menu_message[:w - 15], cp(CP_CYAN))

            self.draw_content_row(h - 2, border_attr)
            leg_text = "★ Ativo   * Modificado   [ROM] Fábrica   [RAM] Personalizado"
            self.safe_add(h - 2, 2, leg_text[:w - 5], cp(CP_PURPLE))

            self.draw_frame_line(h - 1, "╚", "═", "╝", "↑/↓ Navegar  Enter Aplicar  S Gravar RAM  X Excluir  Esc Voltar", cp(CP_YELLOW), border_attr)

            self.screen.refresh()
            key = self.screen.getch()
            if key in (27, ord("p"), ord("P"), ord("q"), ord("Q")):
                return
            if key in (curses.KEY_DOWN, ord("j")):
                selected = min(len(entries) - 1, selected + 1)
            elif key in (curses.KEY_UP, ord("k")):
                selected = max(0, selected - 1)
            elif key in (10, 13, curses.KEY_ENTER):
                self.apply_named_profile(entries[selected]["name"])
                return
            elif key in (ord("s"), ord("S")):
                name = self.prompt_text("Nome do preset RAM: ")
                if not name:
                    menu_message = "Gravação cancelada"
                    continue
                try:
                    saved = save_profile(name, self.settings)
                    self.settings["active_profile"] = saved
                    self.settings["profile_modified"] = False
                    save_config(self.settings)
                    entries = list_profiles(self.settings)
                    selected = next(i for i, item in enumerate(entries) if item["name"] == saved)
                    menu_message = f"Preset gravado com sucesso: {saved}"
                except ValueError as error:
                    menu_message = f"Erro ao gravar: {error}"
            elif key in (ord("x"), ord("X"), curses.KEY_DC):
                item = entries[selected]
                if item["builtin"]:
                    menu_message = "Perfis ROM de fábrica são protegidos contra exclusão"
                    continue
                try:
                    removed = delete_profile(item["name"])
                    if item["active"]:
                        self.apply_named_profile("Natural")
                    entries = list_profiles(self.settings)
                    selected = min(selected, len(entries) - 1)
                    menu_message = f"Preset excluído: {removed}"
                except (KeyError, ValueError) as error:
                    menu_message = f"Erro: {error}"

    def draw(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        if height < 16 or width < 50:
            self.safe_add(0, 0, "Terminal pequeno demais para visual Synthwave (min 50x16)", cp(CP_RED) | curses.A_BOLD)
            self.screen.refresh()
            return

        border_attr = cp(CP_BORDER)
        status = read_status()
        state = status.get("state", "offline")
        good = state == "running"
        active_profile = self.settings.get("active_profile", "Natural")
        modified = " *" if self.settings.get("profile_modified") else ""
        prof_tag = f"PRESET: {active_profile}{modified}"

        # 0: Top Header Frame
        header_title = "⚡ YETI VOICE // SYNTHWAVE '84 ⚡"
        self.draw_frame_line(0, "╔", "═", "╗", header_title, cp(CP_MAGENTA) | curses.A_BOLD, border_attr)
        tag_pos = max(len(header_title) + 5, width - len(prof_tag) - 5)
        prof_attr = cp(CP_YELLOW if modified else CP_CYAN) | curses.A_BOLD
        self.safe_add(0, tag_pos, f"[{prof_tag}]", prof_attr)

        # 1: Subtitle / Grid info
        self.draw_content_row(1, border_attr)
        sub_left = "░▒▓█ BLUE VO!CE █▓▒░"
        sub_mid = "DSP ENGINE 1984"
        sub_right = "YETI NANO • 48 kHz / 24b"
        self.safe_add(1, 2, sub_left, cp(CP_MAGENTA) | curses.A_BOLD)
        self.safe_add(1, 2 + len(sub_left) + 2, sub_mid, cp(CP_CYAN) | curses.A_BOLD)
        if width >= 80:
            self.safe_add(1, width - len(sub_right) - 4, sub_right, cp(CP_PURPLE))

        # 2: Divider before tabs
        self.draw_frame_line(2, "╠", "═", "╣", border_attr=border_attr)

        # 3: Module Tabs (Synthesizer Sound Modules)
        self.draw_content_row(3, border_attr)
        tab_x = 2
        for idx, (name, _) in enumerate(TABS):
            num = idx + 1
            is_active = (idx == self.tab)
            if is_active:
                label = f"⟦ {num:02d}:{name.upper()} ⟧"
                tab_attr = cp(CP_TAB_ACTIVE) | curses.A_BOLD
            else:
                label = f"[{num:02d}:{name}]"
                tab_attr = cp(CP_PURPLE)
            if tab_x + len(label) < width - 2:
                self.safe_add(3, tab_x, label, tab_attr)
                tab_x += len(label) + (2 if width >= 90 else 1)

        # 4: Telemetry Header Divider
        self.draw_frame_line(4, "╠", "═", "╣", "TELEMETRIA DO SISTEMA // VFD-1984", cp(CP_CYAN) | curses.A_BOLD, border_attr)

        # 5: Telemetry Line 1: Engine state, Source
        self.draw_content_row(5, border_attr)
        self.safe_add(5, 2, "ENGINE :", cp(CP_PURPLE))
        if good:
            self.safe_add(5, 11, "[● ATIVO ]", cp(CP_GREEN) | curses.A_BOLD)
        else:
            self.safe_add(5, 11, f"[▲ {state.upper()}]", cp(CP_RED) | curses.A_BOLD)

        src = status.get("source") or "Aguardando dispositivo USB..."
        if "yeti_nano" in src.lower() or "blue_microphones" in src.lower():
            src_display = "Yeti Nano USB (046d:0ab1)"
        elif len(src) > 30:
            src_display = src[:27] + "..."
        else:
            src_display = src
        self.safe_add(5, 24, "FONTE :", cp(CP_PURPLE))
        self.safe_add(5, 32, src_display, cp(CP_CYAN))

        # 6: Telemetry Line 2: Output, Route / Alert
        self.draw_content_row(6, border_attr)
        if status.get("error"):
            err_msg = status["error"]
            if len(err_msg) > width - 18:
                err_msg = err_msg[:width - 21] + "..."
            self.safe_add(6, 2, "ALERTA :", cp(CP_RED) | curses.A_BOLD)
            self.safe_add(6, 11, f"[!] {err_msg}", cp(CP_RED))
        else:
            self.safe_add(6, 2, "SAÍDA  :", cp(CP_PURPLE))
            self.safe_add(6, 11, "Yeti Voice (PipeWire FX)", cp(CP_GREEN))
            self.safe_add(6, 38, "ROTA :", cp(CP_PURPLE))
            self.safe_add(6, 45, "Bus Estéreo Virtual", cp(CP_CYAN))

        # 7: Parameters Header Divider
        self.draw_frame_line(7, "╠", "═", "╣", "PARÂMETROS DO MÓDULO // RACK DSP", cp(CP_MAGENTA) | curses.A_BOLD, border_attr)

        # 8 to height - 4: Parameter Controls
        controls = TABS[self.tab][1]
        top = 8
        bottom = height - 4
        visible = max(1, bottom - top)

        if self.selected < self.scroll:
            self.scroll = self.selected
        if self.selected >= self.scroll + visible:
            self.scroll = self.selected - visible + 1

        for row, control_index in enumerate(range(self.scroll, min(len(controls), self.scroll + visible))):
            curr_y = top + row
            self.draw_content_row(curr_y, border_attr)
            control = controls[control_index]
            value = get_path(self.settings, control.path)
            selected = (control_index == self.selected)

            if selected:
                self.safe_add(curr_y, 2, "►►", cp(CP_YELLOW) | curses.A_BOLD)
            else:
                self.safe_add(curr_y, 2, "  ", 0)

            self.safe_add(curr_y, 5, f"{control_index + 1:02d}", cp(CP_PURPLE) | (curses.A_BOLD if selected else 0))

            label_attr = (cp(CP_YELLOW) | curses.A_BOLD) if selected else cp(CP_CYAN)
            label_text = control.label
            max_label_w = 23
            if len(label_text) > max_label_w:
                label_text = label_text[:max_label_w - 1] + "…"
            self.safe_add(curr_y, 8, f"{label_text:<{max_label_w}}", label_attr)

            val_x = width - 14
            val_str = format_value(value, control)
            val_attr = (cp(CP_YELLOW) | curses.A_BOLD) if selected else cp(CP_CYAN)

            if control.kind == "bool":
                switch_x = val_x
                if value:
                    switch_str = "[■ ATIVO ]"
                    switch_attr = cp(CP_GREEN) | curses.A_BOLD
                else:
                    switch_str = "[□ BYPASS]"
                    switch_attr = cp(CP_GRID)
                if selected:
                    switch_attr |= curses.A_BOLD
                self.safe_add(curr_y, switch_x, switch_str, switch_attr)
                if selected:
                    track_start = 8 + len(label_text) + 2
                    track_len = max(0, switch_x - 2 - track_start)
                    if track_len > 0:
                        self.safe_add(curr_y, track_start, "·" * track_len, cp(CP_GRID))
            else:
                meter_len = 14
                meter_x = max(34, val_x - (meter_len + 4))
                self.draw_meter(curr_y, meter_x, float(value), control.minimum, control.maximum, length=meter_len, is_selected=selected)
                self.safe_add(curr_y, val_x, f"{val_str:>10}", val_attr)
                if selected:
                    track_start = 8 + len(label_text) + 2
                    track_len = max(0, meter_x - 2 - track_start)
                    if track_len > 0:
                        self.safe_add(curr_y, track_start, "·" * track_len, cp(CP_GRID))

        rendered_count = min(len(controls), self.scroll + visible) - self.scroll
        for empty_row in range(rendered_count, visible):
            self.draw_content_row(top + empty_row, border_attr)

        # height - 4: Divider
        self.draw_frame_line(height - 4, "╠", "═", "╣", border_attr=border_attr)

        # height - 3: ROM Presets quickbar
        self.draw_content_row(height - 3, border_attr)
        self.safe_add(height - 3, 2, "ROM BANK:", cp(CP_PURPLE) | curses.A_BOLD)
        cur_preset_x = 12
        builtin_names = list(BUILTIN_PROFILES)
        max_preset_cols = width - 5
        for i, name in enumerate(builtin_names):
            p_text = f"[{i + 1}]"
            n_text = f"{name} "
            needed = len(p_text) + len(n_text) + 1
            if cur_preset_x + needed >= max_preset_cols:
                break
            self.safe_add(height - 3, cur_preset_x, p_text, cp(CP_YELLOW) | curses.A_BOLD)
            cur_preset_x += len(p_text)
            self.safe_add(height - 3, cur_preset_x, n_text, cp(CP_CYAN))
            cur_preset_x += len(n_text) + 1

        # height - 2: Dynamic status / message
        self.draw_content_row(height - 2, border_attr)
        self.safe_add(height - 2, 2, "⚡ STATUS:", cp(CP_MAGENTA) | curses.A_BOLD)
        msg_max_w = width - 15
        disp_msg = self.message[:msg_max_w]
        self.safe_add(height - 2, 12, disp_msg, cp(CP_CYAN))

        # height - 1: Bottom border and help shortcuts
        if width >= 90:
            help_title = "↑/↓ Navegar  ←/→ Ajustar  Espaço Alternar  Tab Seção  P Perfis  D Diag  R Reset  Q Sair"
        else:
            help_title = "↑/↓ Navegar  ←/→ Ajustar  Espaço Alternar  Tab Seção  P Perfis  Q Sair"
        self.draw_frame_line(height - 1, "╚", "═", "╝", help_title, cp(CP_YELLOW), border_attr)
        self.screen.refresh()

    def run(self) -> None:
        ensure_daemon()
        while True:
            self.draw()
            key = self.screen.getch()
            controls = TABS[self.tab][1]
            if key in (ord("q"), ord("Q")):
                return
            if key in (curses.KEY_DOWN, ord("j")):
                self.selected = min(len(controls) - 1, self.selected + 1)
            elif key in (curses.KEY_UP, ord("k")):
                self.selected = max(0, self.selected - 1)
            elif key in (curses.KEY_RIGHT, ord("l"), ord("+")):
                self.adjust(1)
            elif key in (curses.KEY_LEFT, ord("h"), ord("-")):
                self.adjust(-1)
            elif key == ord(" "):
                self.adjust(1)
            elif key in (9, curses.KEY_NPAGE):
                self.tab = (self.tab + 1) % len(TABS)
                self.selected = self.scroll = 0
            elif ord("1") <= key <= ord("8"):
                self.choose_builtin_profile(key - ord("1"))
            elif key in (ord("p"), ord("P")):
                self.profile_menu()
            elif key in (ord("r"), ord("R")):
                self.apply_named_profile("Natural")
                self.message = "Preset Natural restaurado"
            elif key in (ord("d"), ord("D")):
                self.diag_modal()


def main() -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("A TUI requer um terminal interativo.", file=sys.stderr)
        return 2
    curses.wrapper(lambda screen: App(screen).run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
