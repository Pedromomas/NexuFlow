# NexuFlow 1.2 Release Notes

## Network Quality Engine

- Continuous latency, jitter and packet-loss sampling.
- Nexus Score 0–100 with packet loss weighted more heavily than small ping differences.
- Stable neutral reference target shared between observer/daemon so before/after windows stay comparable.
- 20–30 second pre-BOOST baseline and post-BOOST comparison.
- Local session history with quality delta and adaptive events.

## Game profiles

- `roblox`: network/system optimization with conservative endpoint steering only for verified interchangeable pools.
- `riot_safe`: mandatory for VALORANT and League of Legends.
- `valve_safe`: mandatory for Counter-Strike 2.
- `safe`: generic conservative mode.
- `aggressive`: experimental mode for non-protected games only.

When multiple supported games are open, a protected Riot/Valve title takes priority. If a protected title starts while a non-protected BOOST is already active, NexuFlow restores the previous session first and transitions to the protected safe profile.

## Anti-cheat hardening

- Official Riot/Valve guidance re-reviewed on 2026-08-30.
- Protected games never receive process-priority/CPU-set manipulation.
- No memory reading/writing, DLL/code injection, graphics hooks, input automation or game-socket inspection.
- No packet interception/modification/redirection.
- No game file modifications or anti-cheat service/driver manipulation.
- No endpoint firewall steering for Riot/CS2.
- No live DNS/MTU mutation during protected gameplay.
- No TCP registry tweaks, standby purge, service pausing or network resets during protected gameplay.
- CS2 Trusted Mode remains intact; no third-party launch override.
- Low-level mutation managers contain their own protected-runtime guards.
- Build/test pipeline includes a static anti-cheat surface audit.
- Protected gameplay now avoids PowerShell-based adapter/DNS introspection; public DNS diagnostics use direct UDP only.
- Protected route diagnostics are limited to neutral reference targets and arbitrary endpoint benchmarks are disabled.
- Tauri desktop path remains IPC/sidecar based; no persistent development API or PowerShell server is required.

## Route diagnostics and Adaptive Booster

- Read-only TTL-based route diagnostics with latency/jitter/apparent ICMP loss per hop.
- Avoids blaming an isolated ICMP-deprioritizing router; highlights degradation only when it persists.
- Adaptive Booster reacts to sustained quality degradation but does not disrupt live game sockets.
- For protected titles, adaptive behavior remains entirely diagnostic/read-only.

## Windows Gaming Health

- CPU utilization/clocks.
- Memory availability.
- NVIDIA GPU driver/utilization/temperature/P-state when available.
- Network interface/link speed/type/MTU/gateway.
- Active Windows power plan and AC status.
- No injected FPS hook; FPS remains unset until a non-invasive source is available.

## Recovery and distribution

- Persistent state checkpoints before system mutations.
- Stale active sessions are restored before a new BOOST starts.
- Legacy protected-process snapshots are not reopened just for process-local rollback.
- Optional Authenticode signing for the privileged helper/installer.
- PyInstaller UPX compression remains disabled.
