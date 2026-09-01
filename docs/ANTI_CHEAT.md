# NexuFlow 1.5 — Anti-Cheat Compatibility Policy

**Policy version:** 2026.09.01
**Last reviewed:** 2026-09-01
**Scope:** VALORANT, League of Legends, Counter-Strike 2 e sinais genéricos EAC/BattlEye
**Goal:** minimize interaction with anti-cheat protected games rather than trying to hide, bypass, weaken or evade anti-cheat software.

> No third-party optimizer can honestly guarantee a zero-percent enforcement risk. Riot and Valve control their anti-cheat systems, enforcement and future policy changes. NexuFlow therefore uses a deliberately conservative compatibility lockdown and gives up optimizations that would touch a protected game.

## Official guidance reviewed

### Riot Vanguard — VALORANT / League of Legends

The current Riot Vanguard developer FAQ states that external tools that read game memory must change their approach, while tools using supported APIs/game-client/in-game APIs are expected to continue functioning. Riot also states that **there is no Vanguard allow-list**; developers are responsible for redesigning tools that conflict with Vanguard restrictions.

Riot's Terms of Service additionally prohibit unauthorized third-party programs that interact with Riot Services, including software that intercepts, emulates or redirects Riot communications and software that collects information by reading memory used by Riot Services.

Official sources reviewed:

- Riot Games — Vanguard FAQ for Third Party Applications: https://www.riotgames.com/en/DevRel/vanguard-faq
- Riot Developer Relations — Vanguard: https://support-developer.riotgames.com/hc/en-us/articles/28021427366163-Vanguard
- Riot Games — Terms of Service: https://www.riotgames.com/en/terms-of-service
- Riot Developer Relations — General Policies: https://support-developer.riotgames.com/hc/en-us/articles/22698591841939-General-Policies

### Valve VAC / Counter-Strike 2 Trusted Mode

Valve's CS2 Trusted Mode documentation states that Trusted Mode blocks third-party files from interacting with/injecting into CS2 and that there is no injection allow-list. Valve explains that an injection which succeeds while CS2 is protecting itself can be subject to VAC enforcement. Software that requires injection may request the `-allow_third_party_software` launch option; **NexuFlow intentionally never requests or requires that launch mode**.

Valve's VAC documentation describes VAC enforcement for cheat software that gives a player an advantage. NexuFlow therefore avoids game-process modification and leaves CS2 Trusted Mode intact.

Official sources reviewed:

- Steam Support — CS2 Trusted Mode: https://help.steampowered.com/en/faqs/view/09A0-4879-4353-EF95
- Steam Support — Valve Anti-Cheat (VAC): https://help.steampowered.com/en/faqs/view/571A-97DA-70E9-FF74
- Steam Support — VAC secure-server connection errors: https://help.steampowered.com/en/faqs/view/22C0-03D0-AE4B-04E8
- Steam Support — I've been VAC banned: https://help.steampowered.com/faqs/view/647C-5CC1-7EA9-3C29

## Maximum-compatibility lockdown

When VALORANT or League of Legends is detected, the backend **always** resolves to `riot_safe`. When CS2 is detected, it **always** resolves to `valve_safe`. An `aggressive` request cannot bypass this downgrade.

The policy is enforced in multiple layers:

1. profile resolution in `anti_cheat.py`;
2. Orchestrator feature gates;
3. REST mutation endpoint guards;
4. manual service guards;
5. low-level mutation managers themselves;
6. static anti-cheat source audit during tests/build.

This means a future UI bug is not enough to make a protected-game mutation happen.

### Forbidden for protected gameplay

NexuFlow does not perform any of the following while Riot/CS2 protected gameplay is active:

- reading or writing game memory;
- opening protected processes for priority/CPU-set optimization;
- DLL/code injection;
- graphics hooks or injected overlays;
- low-level competitive input automation;
- process module/thread enumeration for game inspection;
- per-process game socket inspection;
- packet interception, packet modification, emulation or redirection;
- modifying protected game executable/DLL/data files;
- manipulating Vanguard/VAC services or drivers;
- installing an anti-cheat-observation/bypass kernel driver;
- endpoint firewall steering for Riot/CS2;
- game process priority changes;
- game process CPU affinity / CPU Sets;
- live DNS mutation during the protected session;
- live MTU mutation during the protected session;
- experimental TCP Registry tweaks;
- standby-list purge;
- service pausing;
- Winsock/IP reset while a protected title is running;
- launching CS2 with the Trusted Mode override.
- launching `powershell.exe` or `pwsh.exe` for any purpose while a protected session is active.
- scanning Windows Update for optional drivers while a protected session is active; the Driver Center is deferred until the game closes.

### Allowed compatibility-safe surface

Protected profiles are deliberately limited to operations external to the protected game:

- ordinary read-only PID/process-name detection;
- system CPU/RAM/GPU/network telemetry;
- NVIDIA telemetry through `nvidia-smi` when available;
- latency/jitter/loss probes to neutral Internet reference targets;
- read-only traceroute diagnostics;
- DNS benchmark without changing the active resolver during protected gameplay;
- read-only PMTU recommendation without changing interface MTU during protected gameplay;
- temporary Windows system power plan with exact rollback;
- local baseline/history/recovery state;
- rollback of general OS/network changes previously made by NexuFlow.

The quality engine does **not** inspect the protected game's packets or live sockets to calculate its score. Its score is a general Internet-quality reference, not a claim to be the exact in-game server latency.

## Legacy rollback rule

An older NexuFlow/Nexus snapshot could theoretically contain process-priority/CPU-set state for a title that is now protected. If that protected process is currently running, NexuFlow 1.5 **will not open it just to restore process-local state**. Windows discards process-local priority/CPU-set state when the process exits. General OS state such as power plan, DNS, MTU and firewall rules remains independently reversible.

## Static build audit

`scripts/anti-cheat-audit.ps1` runs during `test.ps1` and `build.ps1`. It fails the build if the runtime source introduces common injection/memory-hook/packet-driver primitives, anti-cheat-sensitive dependencies, a custom `.sys`/`.asi` payload, or a CS2 Trusted Mode launch override in executable configuration.

This audit is a regression guard, **not** certification by Riot or Valve.

## Distribution guidance

For public distribution:

- keep the normal Tauri UI unprivileged;
- elevate only the narrow helper when a system mutation is actually required;
- code-sign the helper and installer when practical;
- keep UPX disabled for the privileged PyInstaller helper;
- publish version hashes;
- test current VALORANT/LoL/CS2 versions on a clean Windows machine;
- re-review official Riot/Valve policies before each release;
- if an anti-cheat blocks a NexuFlow behavior, remove/disable that behavior rather than attempting to evade the block.

Code signing improves publisher identity and Windows reputation; it is **not** a Vanguard/VAC allow-list and does not guarantee acceptance.
