# Yeti Voice

TUI e engine de áudio para o **Blue Yeti Nano `046d:0ab1`** no Linux. Recria a superfície de controle do Logitech G Hub/Blue VO!CE com PipeWire e FFmpeg, sem dependências Python externas.

## Controles

- Hardware: ganho de captura e volume dos fones via ALSA, quando expostos pelo firmware.
- Broadcast: master, EQ paramétrico de três bandas, passa-altas, redução de ruído, gate/expander, de-esser, de-popper, compressor e limiter.
- Modulação: pitch shifter, flanger/phaser, chorus, reverb, ring modulator e time delay.
- Perfis de fábrica: Natural, Broadcast, Voz Nítida, Rádio, Podcast, Streaming, Reunião e ASMR.
- Perfis personalizados persistentes, incluindo ganho de hardware e todos os efeitos.
- Roteamento: cria o microfone virtual `Yeti Voice (Blue VO!CE)` e pode torná-lo a entrada padrão.

O padrão polar do Nano tem apenas **cardioide** e **omnidirecional**. Por segurança, ele continua sendo selecionado pelo botão traseiro: a Logitech não publica o protocolo HID do modelo e enviar relatórios presumidos pode alterar controles errados no firmware.

## Executar no projeto

```bash
./yeti-voice --diagnose
./yeti-voice
```

## Instalar para o usuário

```bash
./install.sh
yeti-voice
```

O instalador copia a aplicação para `~/.local/share/yeti-voice`, cria `~/.local/bin/yeti-voice` e ativa um serviço `systemd --user`. A configuração fica em `~/.config/yeti-voice/config.json`.

Na TUI: `↑/↓` navegam, `←/→` ajustam, `Espaço` alterna, `Tab` troca seção, `P` abre o gerenciador de perfis, `1`–`8` aplicam perfis de fábrica, `D` diagnostica, `R` restaura e `Q` fecha apenas a interface (o engine continua ativo).

## Perfis

```bash
yeti-voice profile list
yeti-voice profile apply "Podcast"
yeti-voice profile save "Minha Voz" --description "Ajuste para o escritório"
yeti-voice profile show "Minha Voz"
yeti-voice profile delete "Minha Voz"
```

Perfis personalizados ficam em `~/.config/yeti-voice/profiles.json`. Perfis de fábrica ajustam apenas o DSP e preservam o ganho do microfone e o volume dos fones; perfis personalizados também restauram esses dois controles.

## Fluxo de áudio

```text
Yeti Nano físico -> FFmpeg (filtros) -> sink PipeWire nulo -> Yeti Voice (fonte virtual) -> aplicativos
```

## Problema USB detectado nesta máquina

O Nano foi enumerado atrás do hub USB `067b:2586`, mas respondeu com timeouts `-110` ao selecionar as interfaces e ler os controles USB. Isso bloqueia também `amixer`, `pactl` e `wpctl`. A recuperação recomendada é:

1. Desconectar o Nano.
2. Aguardar 10 segundos.
3. Conectá-lo diretamente a uma porta USB do computador, sem o hub.
4. Rodar `yeti-voice --diagnose`; `healthy` deve aparecer como `true`.

O engine fica em `waiting_device` e se conecta automaticamente assim que o microfone reaparecer.

Para apontar o engine manualmente a outra fonte PipeWire/Pulse, defina `YETI_VOICE_SOURCE` com o nome técnico retornado por `pactl list short sources`.
