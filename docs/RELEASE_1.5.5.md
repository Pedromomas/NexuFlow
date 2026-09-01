# NexuFlow 1.5.5 — Driver Edition

## Central de drivers

- Scan iniciado somente quando o usuário clica em **Verificar drivers**.
- Consulta o Windows Update Agent para atualizações de tipo `Driver` ainda não instaladas.
- Mostra somente título, fabricante, modelo, classe, provedor e data fornecidos pelo Windows Update.
- Não exporta hardware ID, device instance ID, caminho de INF ou inventário pessoal.
- Não baixa nem instala drivers automaticamente.
- O botão **Abrir atualizações oficiais** abre `ms-settings:windowsupdate-optionalupdates`, a tela oficial do Windows para revisão e confirmação.
- Se um jogo Riot/Valve/EAC/BattlEye estiver ativo, o scan é adiado antes de iniciar PowerShell ou consultar o Windows Update.

“Nenhuma atualização oferecida” significa apenas que o Windows Update não ofereceu um driver naquele momento. Não é uma afirmação de que toda versão disponível no site do fabricante é idêntica ou mais antiga.

## Polimento e acessibilidade

- A escala de texto agora cobre badges, avisos, histórico, cards de saúde, Latency Lab, diálogos “Saiba mais”, Central de drivers e textos auxiliares.
- Cards passaram a crescer e quebrar linha quando necessário, evitando corte em 120–125%.
- Nenhum novo polling foi adicionado: o scan de drivers é sob demanda, preservando inicialização, CPU e rede.
- A UI continua sem shell arbitrário; os novos comandos Tauri são fixos e sem parâmetros de caminho/URL.

## Segurança mantida

- No-Driver Contract: o NexuFlow continua sem driver próprio.
- Nenhum downloader de driver de terceiros.
- Nenhuma instalação silenciosa, downgrade automático, remoção de pacote ou reinício forçado.
- PowerShell/pwsh continua bloqueado globalmente durante sessões protegidas.
- Modos Ping, PC, Completo e Hardcore Safe permanecem inalterados.
- Policy feed Ed25519 continua disable-only.

## Pacotes

- `NexuFlow-1.5.5-DriverEdition.zip`: pacote de usuário com instalador `.exe`, documentação, SBOM e manifesto.
- `NexuFlow-1.5.5-DriverEdition-Source.zip`: código-fonte preparado para abrir no VS Code e reconstruir com `scripts/setup.ps1 -Desktop`.

