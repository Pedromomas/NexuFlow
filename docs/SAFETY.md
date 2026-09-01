# Safety and rollback policy

NexuFlow distinguishes reversible system tuning from invasive game interaction.

## Quatro modos públicos

- **Ping:** rede e qualidade, respeitando o lockdown do jogo.
- **PC:** desempenho geral reversível do Windows.
- **Completo:** união de Ping e PC.
- **Hardcore Safe:** somente leitura.

Perfis internos de compatibilidade não são aceitos pela API pública. Jogo desconhecido sempre entra em `unknown_safe`, sem herdar mutações de outro catálogo.

## Generic Safe / Roblox

For non-protected games, conservative profiles may benchmark DNS, reduce MTU only after multi-target PMTU agreement, use verified endpoint steering only for explicitly interchangeable pools, apply Above Normal process priority / Windows performance CPU Sets, and use a temporary cloned power plan. Every persistent mutation has rollback state.

## Riot Safe and Valve Safe

VALORANT/LoL and CS2 are handled by dedicated hard profiles. The backend blocks process manipulation, injection/hooks, packet interception, endpoint firewall steering, experimental TCP registry tweaks, standby purge and service pausing. See `ANTI_CHEAT.md` for the reviewed official Riot/Valve guidance and exact guardrails.

## Perfis agressivos legados

O engine ainda entende snapshots legados para rollback, mas a WebView/Tauri 1.5 não aceita `aggressive`, `auto`, `roblox` ou perfis internos como entrada pública. Isso impede que uma tela comprometida escolha diretamente uma política de maior mutação.

## Explicitly excluded

- disabling Microsoft Defender or Windows Firewall;
- disabling Windows Security services;
- guessed cloud-CIDR blocking;
- permanent deletion of services/tasks;
- BCD/timer/HPET folklore tweaks;
- undocumented NVIDIA registry profile hacks;
- game memory reads/writes;
- game DLL/code injection or graphics hooks;
- competitive input automation;
- packet modification/interception;
- anti-cheat driver/service bypass or disabling;
- modification of protected game files.

## Recovery

Persistent state is stored under `%PROGRAMDATA%\NexuFlow\state`. If the previous session snapshot is still active and its daemon is gone, the app reports recovery as required and the daemon attempts stale rollback before another optimization. `Restore All` is idempotent where possible and failed system rollback keeps the snapshot for retry.
