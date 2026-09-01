# Network Quality Engine

NexuFlow 1.2 measures connection quality as a combination of **latency + jitter + packet loss** rather than treating the lowest ping as automatically best.

## Nexus Score (0–100)

The score is intentionally loss-sensitive: packet loss receives the largest penalty, followed by jitter and latency. This means a path with 18 ms latency and substantial loss can score worse than a stable 28 ms path.

The score is a NexuFlow diagnostic metric, not an ISP SLA and not the same thing as the game's own server ping. Protected games are not inspected to discover their live sockets; the quality monitor probes independent Internet reference targets instead.

## Baseline before/after

The unprivileged observer samples roughly once per second. On BOOST, the engine prefers an existing rolling 20–30 second window. On a cold start it waits for enough samples **before any system mutation**. After optimization it captures another window and records:

- median latency;
- jitter;
- packet loss;
- Nexus Score;
- delta before → after.

This makes it possible to distinguish measurable improvement from placebo.

## Auto profiles

- `auto`: selects the policy from the detected game.
- `roblox`: normal local optimizer policy suitable for Roblox; may use verified endpoint steering only when endpoints are explicitly marked interchangeable.
- `riot_safe`: hard anti-cheat policy for VALORANT / League of Legends.
- `valve_safe`: hard anti-cheat policy for CS2 / VAC / Trusted Mode.
- `safe`: generic conservative profile.
- `aggressive`: experimental non-protected-game profile only. Protected games always downgrade in the backend.

## Route diagnostics

The WinMTR-like route diagnostic sends NexuFlow-owned ICMP probes with increasing TTL and reports per-hop median latency, jitter and apparent ICMP loss. It can identify the first hop where a persistent latency jump appears.

Important: routers often deprioritize ICMP replies. High loss at one intermediate hop is not proof that real game traffic is being dropped. Route diagnostics therefore remain **read-only** and never trigger automatic firewall/routing changes by themselves.

NexuFlow does not claim that a hop belongs to Claro/Vivo/Oi or an international carrier unless there is a reliable source for that mapping. The current implementation reports the hop IP and observable behavior rather than inventing ASN/operator ownership.

## Adaptive Booster

During a live game, sustained quality degradation can trigger a reassessment. To avoid disconnecting an active match, the reassessment is deliberately non-disruptive:

- re-benchmark DNS and stage a recommendation for the next connection;
- re-evaluate verified endpoint pools for non-protected games without applying new firewall blocks mid-match;
- run read-only route diagnostics;
- save the event in the session record.

Protected Riot/Valve sessions never receive live endpoint steering or resolver mutation.

## Crash recovery

Every persistent system mutation is snapshotted under `%PROGRAMDATA%\NexuFlow\state`. If an active snapshot exists but the daemon is no longer alive, NexuFlow reports recovery as required. The daemon also attempts stale-session rollback before starting a new optimization. A history-write failure is non-critical and cannot keep an otherwise fully restored system marked dirty.

## Session history

Completed sessions are stored locally under `%LOCALAPPDATA%\NexuFlow\history\sessions.json` with before/after quality, Gaming Health, adaptive events, profile and anti-cheat policy. FPS remains `null` until a non-invasive source is available; NexuFlow will not add graphics hooks merely to populate an FPS number.
