#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
install_dir="${XDG_DATA_HOME:-$HOME/.local/share}/yeti-voice"
bin_dir="$HOME/.local/bin"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
plugin_dir="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/vitor.yeti-voice"
hypr_dir="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"

mkdir -p "$install_dir" "$bin_dir" "$unit_dir"
cp -a "$project_dir/yeti_voice" "$install_dir/"
install -m 0755 "$project_dir/yeti-voice" "$install_dir/yeti-voice"
ln -sfn "$install_dir/yeti-voice" "$bin_dir/yeti-voice"
install -m 0644 "$project_dir/systemd/yeti-voice.service" "$unit_dir/yeti-voice.service"
mkdir -p "$plugin_dir"
install -m 0644 "$project_dir/omarchy/vitor.yeti-voice/BarWidget.qml" "$plugin_dir/BarWidget.qml"
install -m 0644 "$project_dir/omarchy/vitor.yeti-voice/manifest.json" "$plugin_dir/manifest.json"
mkdir -p "$hypr_dir"
install -m 0644 "$project_dir/hypr/yeti-voice.lua" "$hypr_dir/yeti-voice.lua"
systemctl --user daemon-reload
systemctl --user enable yeti-voice.service
systemctl --user restart yeti-voice.service

if command -v omarchy-shell >/dev/null 2>&1; then
  omarchy-shell shell rescanPlugins >/dev/null
  omarchy plugin enable vitor.yeti-voice --section right >/dev/null 2>&1 || true
  omarchy bar move vitor.yeti-voice --section right --after vitor.wireguard >/dev/null 2>&1 || true
fi

printf 'Instalado. Execute: %s/yeti-voice\n' "$bin_dir"
