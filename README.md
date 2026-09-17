<div align="center">

# ⚡ NexuFlow

**Edição Comunidade — 100% gratuita.** Todas as funções implementadas estão disponíveis sem conta, assinatura, trial ou licença paga. Códigos secretos são cosméticos gratuitos. As proteções durante partidas continuam obrigatórias. A versão 2.1 está em revisão para lançamento; não é certificada por fabricantes de anticheat.

### Performance, diagnóstico de latência e segurança para jogos competitivos no Windows

![Windows 10/11](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=for-the-badge&logo=windows&logoColor=white)
![Angular 22](https://img.shields.io/badge/Angular-22-DD0031?style=for-the-badge&logo=angular&logoColor=white)
![Tauri 2](https://img.shields.io/badge/Tauri-2-24C8DB?style=for-the-badge&logo=tauri&logoColor=white)
![Safety First](https://img.shields.io/badge/Safety-Anti--cheat%20first-31C48D?style=for-the-badge&logo=shield&logoColor=white)

**Versão em validação: 2.1 — Edição Comunidade**

[Baixar a versão de revisão 2.1.0-rc.2](https://github.com/Pedromomas/NexuFlow/releases/tag/v2.1.0-rc.2) · [Limitações e testes pendentes](docs/STABLE_GATES.md) · [Relatar vulnerabilidade](SECURITY.md)

Safe Core obrigatório e independente da automação, entrada direta sem cadastro, Central do PC, três temas secretos, DNS comparativo e speed test limitado. O atualizador exige pacotes assinados, mas a distribuição pública ainda depende de publicação e validação. Veja [a revisão da edição gratuita](docs/COMMUNITY_REVIEW_20260917.md). Documentos anteriores sobre contas e monetização são históricos e não definem a edição atual.

</div>

## Apoie se puder

Se o NexuFlow te ajudou, até R$ 1 já dá uma força para continuar o projeto. Se não puder, tudo bem: o aplicativo inteiro continua gratuito. Não há assinatura, recompensa paga ou desbloqueio de funções.

No aplicativo, abra **Apoiar o projeto** para ver o QR Code, copiar a chave ou o Pix Copia e Cola. Valor livre, confirmado somente no seu banco. Confira o destinatário **Pedro Fernandes Bahia Rocha** antes de enviar.

Chave Pix: `eba4282e-5305-4de8-ae77-220a07d831e7`.

![QR Code Pix voluntário, sem valor definido](public/donation-pix.svg)

> O NexuFlow é uma plataforma local para entender e melhorar a experiência de jogo sem promessas mágicas: mede latência, qualidade de rede, saúde do PC e oferece ajustes conservadores com rollback.

## ✨ Por que NexuFlow?

| Área | O que entrega |
|---|---|
| 🌐 **Rede** | Latência, jitter, perda de pacotes, rota e baseline antes/depois. |
| ⚡ **PC** | Saúde de CPU, RAM, GPU, energia e sinais de stutter. |
| 🛡 **Jogos protegidos** | Políticas fail-closed para Riot, Valve, EAC e BattlEye. |
| 🚗 **Driver Center** | Consulta sob demanda ao Windows Update; nunca baixa ou instala drivers sozinho. |
| 🎨 **Visual Edition** | Oito temas públicos e três universos secretos locais que transformam toda a interface. |
| 🔎 **Transparência** | Histórico local, relatórios exportáveis e explicação clara de cada modo. |

## 🎮 Recursos principais

- **Nexus Latency Lab:** transforma dados de rede e sistema em um diagnóstico compreensível.
- **Ping, PC, Completo e Hardcore Safe:** modos independentes para que o usuário saiba exatamente o que cada escolha faz.
- **Protected Session Shield:** sessão protegida limita o NexuFlow a ações compatíveis e bloqueia superfícies arriscadas.
- **Central de Drivers 1.5.5:** mostra atualizações que o próprio Windows oferece e encaminha para a tela oficial de atualizações opcionais.
- **Aparência 1.5.7:** galeria independente com Nebula, Midnight, Emerald, Alto Contraste, Blocos, Relíquia, Tático e Operação.
- **Arte Secreta 1.5.8:** código cosmético validado localmente libera ícone, mascote e capa exclusivos na galeria.
- **Refino 1.5.9:** mistério total antes do resgate, mascote PNG transparente, ícone recortado e paleta azul, vermelha e branca.
- **Trust Edition 1.6:** Modo Investigador, allowlist estrutural, relatório Ed25519 local, manifesto de confiança e pacote-fonte determinístico.
- **Flux:** mascote original do NexuFlow, sem personagens, logos ou arte de terceiros.
- **Privacy by default:** dados ficam locais; não há telemetria externa obrigatória.

> **Compromisso de segurança:** o NexuFlow não instala driver próprio, não intercepta tráfego, não injeta código, não altera memória de jogos e não tenta substituir a infraestrutura global de relay de serviços como ExitLag ou NoPing.

## 🧭 Navegação

[Instalação](docs/INSTALL.md) · [Manifesto de confiança](TRUST_MANIFEST.md) · [Segurança](SECURITY.md) · [Allowlist de rede](docs/NETWORK_ALLOWLIST.md) · [Build verificável](docs/BUILD_REPRODUCIBILITY.md) · [Compatibilidade anti-cheat](docs/ANTI_CHEAT.md) · [Validação](docs/VALIDATION.md) · [Histórico de versões](releases/README.md)

## Stack

- **Desktop/UI:** Angular 22 + Ionic 9 + Tailwind CSS 4.
- **Desktop host:** Tauri 2.
- **API local de desenvolvimento:** FastAPI + Uvicorn em `127.0.0.1:8000`.
- **Engine:** Python 3.12+ (compatível com Python 3.14) + `psutil`.
- **Windows:** Windows ICMP API, CPU Sets, `powercfg`, `netsh`, Registry e NT APIs. PowerShell é usado apenas fora de sessões protegidas; durante Riot/Valve/EAC/BattlEye seu lançamento é bloqueado globalmente.

O desktop Tauri é o caminho principal: a UI continua sem privilégio administrativo e o sidecar Python solicita UAC apenas quando uma operação privilegiada é necessária. O aplicativo instalado **não precisa manter VS Code, Node dev server ou FastAPI abertos**.

Para desenvolver com o motor funcionando, use `npm run dev` ou a tarefa do VS Code **NexuFlow: Abrir aplicativo completo**. `npm run ionic:serve` abre somente uma prévia visual no navegador e, por projeto, não possui acesso ao motor desktop.

## Segurança e rollback

- WebView/Tauri sem privilégio administrativo.
- Helper Python é a única camada que solicita UAC.
- FastAPI de desenvolvimento escuta somente em loopback e mutações exigem `X-NexuFlow-Token`.
- CORS restrito às origens locais de desenvolvimento.
- Toda alteração persistente do BOOST é salva em `%PROGRAMDATA%\NexuFlow\state` antes/de acordo com checkpoints de mutação.
- Snapshots antigos de `%PROGRAMDATA%\NexusBooster` podem ser migrados para preservar capacidade de rollback.
- Sessão interrompida é detectada; o daemon restaura estado antigo antes de iniciar uma nova otimização.
- Reset de Winsock/IP nunca é executado automaticamente pelo BOOST.
- Falha ao gravar histórico não impede a limpeza de um snapshot que já foi restaurado com sucesso.

## Anti-cheat: políticas autoritativas no backend

NexuFlow não promete “0% chance de ban”: somente os fornecedores dos jogos controlam enforcement. A política foi revisada novamente em **04/09/2026** contra as páginas oficiais de Vanguard, Termos da Riot, VAC/CS2 Trusted Mode, Roblox, EAC e BattlEye. Em vez de tentar esconder ou contornar anticheat, o backend entra em **maximum-compatibility lockdown** e deliberadamente abre mão de otimizações que tocariam o jogo protegido.

### Riot Safe — VALORANT / League of Legends

VALORANT e LoL forçam `riot_safe`. O perfil não lê/escreve memória do jogo, não abre o processo protegido para prioridade/CPU Sets, não injeta DLL/código, não cria hooks, não automatiza input, não inspeciona sockets do jogo, não intercepta/emula/redireciona comunicações Riot, não toca em Vanguard, não faz firewall steering para Riot, não aplica TCP experimental, não limpa Standby List e não pausa serviços. **DNS e MTU viram diagnóstico-only durante a sessão protegida**; o NexuFlow bloqueia todo lançamento de PowerShell/pwsh enquanto Riot/Valve/EAC/BattlEye estiverem ativos, restringe traceroute a alvos neutros e desativa benchmark arbitrário de endpoints. A única mutação de desempenho mantida é o plano de energia geral do Windows, com rollback.

### Valve Safe — Counter-Strike 2

Além de preservar Trusted Mode e evitar qualquer injection/hook, a v1.5 bloqueia completamente PowerShell/pwsh durante o CS2. A própria Valve lista PowerShell entre softwares que podem contribuir para erro de conexão VAC-secure; isso não é descrito como ban automático, mas o NexuFlow elimina essa superfície durante a partida.

CS2 força `valve_safe`, inclusive quando `aggressive` foi solicitado. NexuFlow preserva o Trusted Mode: não injeta em CS2, não exige o launch override de terceiros, não modifica executáveis/DLLs/arquivos do jogo, não abre o processo para otimização, não inspeciona sockets e não faz endpoint firewall steering enquanto o jogo protegido está ativo.

Leia a revisão e fontes oficiais em [`docs/ANTI_CHEAT.md`](docs/ANTI_CHEAT.md).

## Network Quality Engine

O dashboard não usa apenas ping. A qualidade é calculada continuamente usando:

- latência mediana;
- jitter;
- packet loss;
- **Nexus Score 0–100**, com perda de pacotes recebendo peso maior que pequenas diferenças de ping.

### Baseline antes/depois

O observer não privilegiado mantém uma janela de amostras. Ao ativar BOOST, o engine usa aproximadamente 20–30 s de dados anteriores e, em cold start, aguarda amostras suficientes **antes de alterar o Windows**. Depois captura outra janela e mostra a diferença de ping/jitter/loss/score.

### Modos públicos e proteção automática

- `ping` — qualidade de conexão e ajustes de rede permitidos.
- `pc` — desempenho geral reversível do Windows.
- `complete` — combina Ping e PC.
- `hardcore_safe` — somente diagnóstico e relatório.

`riot_safe`, `valve_safe`, `protected_safe` e `unknown_safe` são camadas internas automáticas. A WebView não pode pedir perfis legados ou agressivos.

### Diagnóstico de rota

Traceroute/WinMTR-like interno usando ICMP próprio e TTL crescente. Mostra hops, latência, jitter e perda aparente e aponta onde uma degradação persistente parece começar. **É diagnóstico somente-leitura**: perda de ICMP em hop intermediário não é usada como prova nem gera mudança automática.

### Adaptive Booster

Se a qualidade piorar de forma sustentada durante uma partida, o daemon reavalia DNS, endpoint candidates (somente jogos não protegidos) e rota. Para não derrubar sessão ativa, a reavaliação é read-only e salva recomendações/eventos; não troca DNS nem adiciona firewall blocks no meio da partida.

Detalhes em [`docs/NETWORK_QUALITY.md`](docs/NETWORK_QUALITY.md).

## Windows Gaming Health

O NexuFlow mostra, sem sair desligando serviços indiscriminadamente:

- CPU, clocks e possível restrição de clock sob carga;
- RAM total/disponível;
- GPU NVIDIA, driver, utilização, temperatura, P-state/power quando `nvidia-smi` disponibiliza;
- interface de rede, Wi-Fi/Ethernet, link speed, MTU e gateway;
- link negociado de 100 Mbps versus 1/2.5 Gbps;
- plano de energia atual e alimentação AC.

Thermal throttling de CPU não é inventado: sem telemetria específica do fabricante, o app reporta apenas sinais compatíveis/possíveis.

## Visual Edition 1.5.7

Aparência agora é uma área própria da barra lateral, separada dos ajustes do sistema. Os quatro temas de atmosfera são criações originais e aparecem identificados como **“arte original, não afiliado”**. Nenhum tema usa personagem, logo, mapa ou splash art de Roblox, Riot ou Valve.

A marca lateral, a navegação e o raio do BOOST foram redesenhados em SVG. Blocos, Relíquia, Tático e Operação também trocam emblema, ícone de Jogos, geometria e textura da interface — não são apenas uma mudança de cor.

O Dashboard foi reorganizado para destacar Nexus Score, latência, CPU/RAM e GPU, mostrar o jogo uma única vez e diferenciar visualmente os quatro sinais de origem do lag. “Confiança sem conclusão” continua visível quando os dados não permitem afirmar uma causa.

Animações usam somente opacidade e transformação curta, respeitam a opção Movimento reduzido e não adicionam polling, acesso a processo, rede ou anticheat.

## Secret Art Edition 1.5.8

Uma nova aba **Código secreto** fica abaixo de Ajustes. A chave é transformada e comparada localmente; o texto digitado não é salvo nem enviado. Quando aceita, a preferência de desbloqueio fica somente neste computador e revela uma nona aparência original com ícone, mascote e capa próprios.

O desbloqueio é uma surpresa cosmética entre amigos, não um sistema de autenticação ou licença. Ele não concede recursos de engine, não altera o BOOST e não expande a allow-list do Tauri.

### Refino 1.5.9

A tela bloqueada não carrega nem mostra nenhuma arte secreta. Depois do código correto, a capa é revelada, o mascote passa a usar o PNG transparente fornecido pelo criador e o tema ganha identidade azul, vermelha e branca. O emblema lateral também recebeu recorte próprio para esconder o fundo do JPG original.

## Driver Center 1.5.5

O scan de drivers é manual e consulta o Windows Update Agent somente quando o usuário pede. Ele lista atualizações de driver oferecidas pela Microsoft, sem baixar ou instalar nada. A instalação permanece na tela oficial de Atualizações opcionais do Windows, onde o usuário revisa e confirma cada item.

O relatório não expõe hardware ID, device instance ID, caminho de INF ou arquivos pessoais. Durante Riot/Valve/EAC/BattlEye, o scan é adiado antes de iniciar PowerShell. “Nenhuma atualização oferecida” não é apresentado como prova de que todo fabricante publicou a mesma versão.

## Histórico de sessões

Histórico local em `%LOCALAPPDATA%\NexuFlow\history\sessions.json`, com jogo, perfil pedido/efetivo, anti-cheat, antes/depois, Gaming Health e eventos adaptativos. FPS permanece vazio até existir uma fonte não invasiva; o NexuFlow não instala hook gráfico só para medir FPS.

## Rede e sistema

Para jogos não protegidos, conforme perfil e segurança:

- interface IPv4 padrão dinâmica;
- benchmark DNS UDP real para DNS atual, Cloudflare, Google e Quad9;
- PMTU conservador com ICMP/DF;
- endpoint benchmark e steering apenas em pools explicitamente intercambiáveis;
- firewall outbound limitado ao executável;
- `NetworkThrottlingIndex`, `TcpAckFrequency` e `TCPNoDelay` somente no Aggressive não protegido;
- plano de energia temporário clonado e reversível;
- CPU Sets/prioridade para jogos não protegidos;
- standby purge/serviços apenas no Aggressive não protegido.

## Abrir no VS Code

Abra `NexuFlow.code-workspace`.

Preparar ambiente:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1 -Desktop
```

Desktop Tauri:

```powershell
.\scripts\dev.ps1
```

Modo Ionic + FastAPI (desenvolvimento): em um terminal rode `.\scripts\run-api.ps1`; em outro, `.\scripts\dev-ionic.ps1`. O token só existe para o transporte FastAPI de desenvolvimento e fica oculto no app Tauri instalado.

## API de desenvolvimento

Swagger: `http://127.0.0.1:8000/docs`

Leituras principais:

```text
GET /api/v1/health
GET /api/v1/telemetry
GET /api/v1/games
GET /api/v1/diagnostics
GET /api/v1/dns/benchmark
GET /api/v1/gaming-health
GET /api/v1/history
GET /api/v1/recovery
GET /api/v1/anti-cheat
GET /api/v1/route-diagnostics
```

Mutações exigem token e têm guardrails anti-cheat no próprio serviço/backend, não apenas na UI. `scripts/anti-cheat-audit.ps1` também roda nos testes/builds e falha se aparecer superfície de injection/memory-hook/packet-driver ou configuração que desative o Trusted Mode.

## Build do aplicativo Windows

```powershell
.\scripts\build.ps1
```

O build roda doctor, testes, empacota o Python com PyInstaller, testa Angular e cria o instalador Tauri/NSIS. A saída esperada é:

```text
src-tauri\target\release\bundle\nsis\
```

Depois de instalado, o fluxo normal é `NexuFlow.exe → Tauri IPC → nexus-engine.exe`; não é necessário deixar VS Code/Uvicorn/ng serve rodando.

## Testes

```powershell
.\scripts\test.ps1
```

Os scripts usam uma pasta `.pytest-tmp` dentro do projeto para evitar o problema de permissão que algumas instalações Windows apresentam em `%TEMP%\pytest-of-<user>`.

## Smart Route: limite físico

Bloquear endpoint pode induzir um cliente a selecionar outro endpoint equivalente, mas não muda BGP/peering da operadora para o mesmo destino. Para contornar uma rota ruim da Claro/Vivo/Oi até o mesmo servidor, um produto estilo ExitLag precisa de relays/túneis próprios. NexuFlow 1.2 continua sendo um otimizador local e não apresenta endpoint steering como túnel.

## Estrutura

```text
NexuFlow/
├── app/                         # FastAPI + módulos de desenvolvimento/manual
├── engine/
│   └── src/nexus_engine/
│       ├── anti_cheat.py
│       ├── network/
│       │   ├── quality.py
│       │   ├── route_diagnostics.py
│       │   └── ...
│       ├── hardware/
│       │   ├── health.py
│       │   └── ...
│       ├── daemon.py
│       ├── history.py
│       ├── orchestrator.py
│       └── telemetry.py
├── src/                         # Angular/Ionic UI
├── src-tauri/                   # Tauri/Rust IPC
├── docs/
└── scripts/
```

## Requisitos de build

- Windows 10/11 x64.
- Node.js 22.22.3+ em linha suportada pelo Angular 22.
- Python 3.12+; Python 3.14 suportado.
- Rust stable + Cargo + MSVC Build Tools.
- WebView2.
- NVIDIA opcional.

O source é validado com testes de lógica e sintaxe fora do Windows, mas `netsh`, Registry, UAC, CPU Sets, PowerCfg e NT APIs só podem ser validados integralmente num Windows real. Antes de distribuir publicamente, faça smoke test em máquina limpa, assine os binários quando possível e revise novamente as políticas Riot/Valve.
