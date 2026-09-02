# Validação — NexuFlow 1.6

## Portões automatizados

- **112 testes Python aprovados** para engine, API e limites do desktop antes do build final.
- Testes Angular aprovados antes do build final, incluindo escala de texto, temas públicos, bloqueio local da Arte Secreta, status visuais do diagnóstico e presença da Central de drivers.
- Inspeção visual local do Dashboard, galeria de temas, troca de tema, alto contraste, escala de texto em 125% e janela compacta sem rolagem horizontal.
- Compilação do host Rust/Tauri e geração do instalador NSIS.
- Auditoria estática anti-cheat para bloquear APIs de leitura/escrita de memória remota, injeção, hooks, automação de input, packet drivers e a opção que reduz o Trusted Mode do CS2.
- No-Driver Contract para bloquear `.sys`, `.asi`, WinRing0, inpoutx64, WinDivert, Npcap e filtros de pacote.
- Testes de bloqueio global de PowerShell/pwsh durante sessão protegida e rollback sem PowerShell.
- Testes de Unknown Game Safe, Riot/Valve/EAC/BattlEye, allow-list IPC, assinatura Ed25519, expiração, anti-rollback, JSON duplicado e disable-only.
- Testes do Latency Budget, NIC Health, Game Mode, Stutter Health e Session Guard Advisor.
- Testes do Driver Center: adiamento em jogo protegido, minimização de dados, resultado conservador e ausência de download/instalação silenciosa.
- Smoke test real do Windows Update Agent concluído com `ResultCode=2` (sucesso), sem download ou instalação.
- SBOM CycloneDX, manifesto SHA-256 do pacote e SHA-256 do ZIP.

Esses resultados são do ambiente de fechamento em 01/09/2026. Um teste automatizado reduz regressões, mas não é certificação da Riot, Valve, Epic/EAC ou BattlEye.

## Verificações manuais ainda necessárias antes de publicação comercial

- Smoke test em Windows 10 e Windows 11 limpos.
- Abrir, ativar/desativar e desinstalar o instalador final.
- Confirmar UAC único, ausência de janela CMD e rollback após encerramento inesperado.
- Testar adaptadores Intel, Realtek e Wi-Fi sem aplicar automaticamente propriedades de driver.
- Testar resultados do Windows Update em máquinas com atualizações opcionais de GPU, rede e áudio disponíveis.
- Testar as versões atuais de VALORANT, League of Legends, CS2 e ao menos um título EAC/BattlEye.
- Assinar o helper e o instalador com certificado Authenticode comercial.
- Revalidar páginas oficiais dos anticheats imediatamente antes da publicação.

Nem teste local nem assinatura de código garantem risco zero de ban. Somente o fornecedor do jogo controla enforcement.
