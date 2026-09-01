# Performance budget

NexuFlow minimizes runtime interference rather than promising an artificial fixed RAM number.

## Runtime design

- Tauri/WebView UI rather than bundled Electron/Chromium.
- One persistent unprivileged observer instead of spawning the PyInstaller engine on every UI refresh.
- Network-quality sampling is roughly 1 Hz and uses NexuFlow-owned ICMP probes; it is not per-packet interception.
- Game discovery is low-frequency and protected games are classified from ordinary process-name metadata only.
- NVIDIA telemetry uses cached `nvidia-smi` reads.
- Privileged optimizer daemon exists only while BOOST is armed.
- No per-frame hooks, DLL injection, ETW game snooping, process-memory polling or game-socket inspection.
- Adaptive reassessment is cooldown-limited and only triggers after sustained quality degradation; it does not repeatedly mutate a live match.

## Memory target

A strict `<50 MB total working set` cannot be guaranteed for Angular + WebView2 + Python across Windows releases. WebView2 accounting can include shared runtime processes. If a hard memory ceiling becomes a product requirement, the observer/daemon boundary is designed so those components can later migrate to Rust.

## Gaming-first constraints

The engine avoids busy loops, uses lifecycle transitions for mutations/rollback, does not benchmark continuously at high frequency, and refuses to add FPS/game metrics that would require graphics hooks or invasive process access.
