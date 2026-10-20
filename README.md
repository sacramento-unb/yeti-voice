# Yeti Voice

Yeti Voice is a local terminal interface and audio engine for the **Blue Yeti
Nano (`046d:0ab1`)** on Linux. It combines ALSA hardware controls with a
PipeWire/PulseAudio virtual source and an FFmpeg DSP chain, without external
Python packages.

[Documentação em português](docs/README.pt-BR.md) ·
[Architecture](docs/architecture.md)

## What is implemented

- Capture gain and headphone volume control through ALSA, when exposed by the
  device firmware.
- High-pass filtering, noise reduction, gate/expander, three-band parametric
  EQ, de-esser, low-frequency plosive reduction, compression and limiting.
- Optional pitch shifting, flanger, chorus, reverb, ring modulation and delay.
- Eight built-in profiles plus persistent custom profiles.
- A PipeWire virtual microphone named `Yeti Voice (Blue VO!CE)`.
- Device diagnostics and automatic recovery when the microphone disappears.
- Optional Omarchy bar and Hyprland integration.

The Nano's cardioid/omnidirectional polar pattern remains controlled by its
physical rear button. The project deliberately does not send undocumented HID
reports to the microphone firmware.

## Requirements

- Linux with PipeWire's PulseAudio compatibility layer;
- Python 3.10 or newer;
- FFmpeg with the filters used by the selected profile;
- `pactl` and `amixer`;
- Blue Yeti Nano `046d:0ab1` for automatic hardware detection;
- a terminal with curses support for the interactive interface.

The optional pitch effect needs FFmpeg's `rubberband` filter. Omarchy and
Hyprland are required only for their respective desktop integrations.

## Run from the checkout

Diagnostics are read-only:

```bash
./yeti-voice --diagnose
```

Start the terminal interface without installing it:

```bash
./yeti-voice
```

Print the active FFmpeg filter chain:

```bash
./yeti-voice --print-chain
```

The audio engine is normally started by the user service. For a foreground
development run, use `./yeti-voice --daemon`.

## User installation

Review `install.sh` before running it. The installer:

1. copies the application to `~/.local/share/yeti-voice`;
2. links the CLI at `~/.local/bin/yeti-voice`;
3. installs and restarts a `systemd --user` service;
4. installs the optional Omarchy widget and Hyprland rule;
5. asks Omarchy to rescan and enable the widget when `omarchy-shell` exists.

It does not install system packages. Once the runtime requirements are present:

```bash
./install.sh
yeti-voice
```

User settings are stored in `~/.config/yeti-voice/config.json`; custom profiles
are stored in `~/.config/yeti-voice/profiles.json`.

## Controls and profiles

In the TUI, use `↑/↓` to navigate, `←/→` to adjust, `Space` to toggle, `Tab` to
change sections, `P` to manage profiles, `1`–`8` to apply built-in profiles,
`D` for diagnostics, `R` to restore defaults, and `Q` to close the interface.
Closing the TUI does not stop the audio service.

Profiles can also be managed from the CLI:

```bash
yeti-voice profile list
yeti-voice profile apply "Podcast"
yeti-voice profile save "My Voice" --description "Office setup"
yeti-voice profile show "My Voice"
yeti-voice profile delete "My Voice"
```

Built-in profiles change DSP settings while preserving microphone gain and
headphone volume. Custom profiles include both hardware levels and DSP settings.

## Audio flow

```mermaid
flowchart LR
    mic["Blue Yeti Nano"] --> ffmpeg["FFmpeg DSP chain"]
    ffmpeg --> sink["PipeWire null sink"]
    sink --> source["Yeti Voice virtual source"]
    source --> apps["Recording and communication apps"]
```

See [the architecture document](docs/architecture.md) for component boundaries,
configuration flow and failure recovery.

## Tests

The unit suite does not need audio hardware and redirects profile writes to
temporary directories:

```bash
python -m unittest discover -v
python -m compileall -q yeti_voice yeti-voice
```

The tests cover DSP-chain construction, built-in and custom profiles, mocked
ALSA control selection, and the terminal interface. They do not verify acoustic
quality, FFmpeg filter availability, PipeWire routing or behavior on every Yeti
Nano firmware revision.

## Known limitations

- Hardware gain and headphone control depend on ALSA controls exposed by the
  connected firmware.
- DSP profile values are implementation defaults, not calibrated measurements.
- The engine targets one local user session and one Yeti Nano source.
- There is no repository-level license file. Confirm licensing before reusing
  or redistributing the project.

## Troubleshooting

If `--diagnose` reports USB, ALSA or PipeWire timeouts, disconnect the microphone,
wait ten seconds, and reconnect it directly to the computer instead of through a
hub. The engine remains in `waiting_device` and retries when the source returns.

To use another PipeWire/PulseAudio source explicitly, set `YETI_VOICE_SOURCE` to
the technical source name returned by `pactl list short sources`.
