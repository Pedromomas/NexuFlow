# Architecture

## Trust boundaries

```text
Angular WebView (unprivileged)
        │ invoke only
        ▼
Tauri Rust command allow-list + telemetry cache
        │                    │
        │                    └── persistent Python observer (unprivileged)
        │ sidecar request
        ▼
Python helper (unprivileged validation)
        │ Windows UAC runas
        ▼
Python daemon (administrator)
        │
        ├── network mutations
        ├── process/CPU-set mutations
        ├── temporary power scheme
        └── reversible aggressive tweaks
```

The frontend never receives general-purpose command execution. Its privileged boundary accepts only `start`/`restore` and the four public modes (`ping`, `pc`, `complete`, `hardcore_safe`). Running the helper elevated for the desktop session does not expand that allow-list. The observer only measures state; it has no administrative token and performs no system mutation.

During Riot/Valve/EAC/BattlEye sessions, the central command runner rejects every `powershell.exe`/`pwsh.exe` launch before process creation. Native rollback tools remain independently allow-listed; process-local rollback is deferred rather than opening a protected process.

## Boost lifecycle

```text
BOOST clicked
  → UAC
  → daemon starts
  → currently running supported game?
       yes: snapshot → optimize → mark active
       no: arm watcher
  → game launches later
       snapshot → optimize
  → game exits / STOP / Restore All
       firewall → DNS → MTU → TCP registry → process → power → services rollback
```

## Why a daemon

A one-shot optimizer cannot reliably restore state if the UI closes before the game. The elevated helper therefore stays alive at a low polling cadence while NexuFlow is armed. The UI can close without leaving permanent changes; when the game exits, the daemon performs rollback.

## Smart routing

The `SmartRoutePolicy` operates only inside a catalog pool explicitly marked `interchangeable=true`. A pool must represent multiple endpoints that serve the same game function and region. Authentication, patching and matchmaking endpoints must never be mixed with match-server pools.

Scoring heavily penalizes loss, then jitter, then latency. A silent ICMP endpoint is excluded from comparison rather than blocked.

## Future relay architecture — not part of 1.5

For true route control across poor Brazilian ISP peering/CGNAT paths, add:

```text
Client → encrypted UDP tunnel → NexuFlow São Paulo relay → game ASN
                       └──────→ NexuFlow Rio/Curitiba relay (alternate)
```

The client can probe relays and direct paths, select the best route, and use multipath/failover. That is the point where NexuFlow becomes an ExitLag-class networking product rather than a local optimizer.
