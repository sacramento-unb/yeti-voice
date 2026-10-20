# Yeti Voice

Yeti Voice é uma interface de terminal e uma engine de áudio local para o
**Blue Yeti Nano (`046d:0ab1`)** no Linux. O projeto combina controles de
hardware ALSA com uma fonte virtual PipeWire/PulseAudio e uma cadeia DSP do
FFmpeg, sem dependências Python externas.

[README in English](../README.md) · [Arquitetura](architecture.md)

## Funcionalidades implementadas

- Ganho de captura e volume dos fones via ALSA, quando expostos pelo firmware.
- Filtro passa-altas, redução de ruído, gate/expander, EQ paramétrico de três
  bandas, de-esser, redução de plosivas, compressor e limiter.
- Pitch shifter, flanger, chorus, reverb, ring modulator e delay opcionais.
- Oito perfis de fábrica e perfis personalizados persistentes.
- Microfone virtual PipeWire chamado `Yeti Voice (Blue VO!CE)`.
- Diagnóstico do dispositivo e recuperação automática após desconexões.
- Integrações opcionais para a barra do Omarchy e regras do Hyprland.

O padrão polar cardioide/omnidirecional do Nano continua selecionado pelo botão
traseiro. O projeto não envia relatórios HID não documentados ao firmware.

## Requisitos

- Linux com a camada de compatibilidade PulseAudio do PipeWire;
- Python 3.10 ou superior;
- FFmpeg com os filtros usados pelo perfil selecionado;
- `pactl` e `amixer`;
- Blue Yeti Nano `046d:0ab1` para detecção automática;
- terminal com suporte a curses para a interface interativa.

O efeito de pitch requer o filtro `rubberband` do FFmpeg. Omarchy e Hyprland são
necessários somente para suas respectivas integrações.

## Executar no projeto

O diagnóstico é somente leitura:

```bash
./yeti-voice --diagnose
```

Para abrir a interface sem instalar:

```bash
./yeti-voice
```

Para exibir a cadeia de filtros ativa:

```bash
./yeti-voice --print-chain
```

O serviço de usuário normalmente inicia a engine. Para desenvolvimento em
primeiro plano, use `./yeti-voice --daemon`.

## Instalação para o usuário

Revise `install.sh` antes de executá-lo. O instalador:

1. copia a aplicação para `~/.local/share/yeti-voice`;
2. cria o link da CLI em `~/.local/bin/yeti-voice`;
3. instala e reinicia um serviço `systemd --user`;
4. instala o widget opcional do Omarchy e a regra do Hyprland;
5. pede ao Omarchy para redetectar e habilitar o widget quando disponível.

O script não instala pacotes do sistema. Com os requisitos já disponíveis:

```bash
./install.sh
yeti-voice
```

A configuração fica em `~/.config/yeti-voice/config.json`; perfis personalizados
ficam em `~/.config/yeti-voice/profiles.json`.

## Controles e perfis

Na TUI: `↑/↓` navegam, `←/→` ajustam, `Espaço` alterna, `Tab` troca seção, `P`
abre o gerenciador de perfis, `1`–`8` aplicam perfis de fábrica, `D` diagnostica,
`R` restaura e `Q` fecha apenas a interface. Fechar a TUI não encerra a engine.

```bash
yeti-voice profile list
yeti-voice profile apply "Podcast"
yeti-voice profile save "Minha Voz" --description "Ajuste para o escritório"
yeti-voice profile show "Minha Voz"
yeti-voice profile delete "Minha Voz"
```

Perfis de fábrica preservam ganho do microfone e volume dos fones. Perfis
personalizados incluem esses níveis de hardware e os ajustes DSP.

## Fluxo de áudio

```mermaid
flowchart LR
    mic["Blue Yeti Nano"] --> ffmpeg["Cadeia DSP do FFmpeg"]
    ffmpeg --> sink["Sink nulo do PipeWire"]
    sink --> source["Fonte virtual Yeti Voice"]
    source --> apps["Aplicativos de gravação e comunicação"]
```

## Testes

```bash
python -m unittest discover -v
python -m compileall -q yeti_voice yeti-voice
```

Os testes cobrem a construção da cadeia DSP, perfis, seleção simulada de
controles ALSA e a interface de terminal. Eles não validam qualidade acústica,
disponibilidade dos filtros FFmpeg, roteamento real do PipeWire nem todas as
revisões de firmware.

## Limitações conhecidas

- Controles de hardware dependem do que o firmware expõe ao ALSA.
- Os valores dos perfis são padrões de implementação, não medições calibradas.
- A engine atende uma sessão local e uma fonte Yeti Nano.
- Não existe um arquivo de licença no nível do repositório. Confirme o
  licenciamento antes de reutilizar ou redistribuir o projeto.

## Solução de problemas

Se `--diagnose` indicar timeout USB, ALSA ou PipeWire, desconecte o microfone,
aguarde dez segundos e conecte-o diretamente ao computador, sem hub. A engine
permanece em `waiting_device` e tenta novamente quando a fonte reaparece.

Para indicar outra fonte PipeWire/PulseAudio, defina `YETI_VOICE_SOURCE` com o
nome técnico retornado por `pactl list short sources`.
