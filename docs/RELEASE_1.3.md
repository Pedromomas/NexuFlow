# NexuFlow 1.3 Release Notes

## Clean Desktop Mode

- The packaged `nexus-engine` helper is now built with PyInstaller `--windowed`.
- Tauri read-only IPC no longer depends on sidecar stdout/stderr. Telemetry and RPC responses use atomic JSON files under the user's temp directory.
- The production app therefore does not flash a CMD/console window when the observer or helper starts.
- Child Windows commands remain launched with `CREATE_NO_WINDOW`.

## Safer UAC experience

- Applying **new privileged system mutations** still uses the normal Windows UAC boundary. NexuFlow does not disable, suppress or bypass UAC.
- Normal **STOP** no longer launches a second elevated helper. The medium-integrity desktop app sends a one-way rollback signal; the already-elevated daemon owns the restore and exit.
- The rollback signal lives in a user-writable control path and can only request STOP. It cannot request a new privileged optimization, avoiding a reusable privilege-escalation channel.
- Emergency restore uses the same no-prompt path while the elevated daemon is alive; stale privileged snapshots still require UAC.

## UI / UX polish

- Four persisted themes: Nebula, Midnight, Emerald and High Contrast.
- Text scaling from 90% to 125%.
- Reduced-motion mode with automatic `prefers-reduced-motion` support.
- Keyboard focus rings, skip link and Alt+1…Alt+4 navigation shortcuts.
- Lightweight page/card transitions using only opacity/transform where possible.
- Floating scroll hotbar for top, accessibility controls and bottom.
- Custom scrollbars and improved responsive layout.
- Appearance settings persist locally and never affect optimization/anti-cheat policy.

## Anti-cheat policy

NexuFlow 1.3 keeps the 1.2 Riot/Vanguard and Valve/VAC lockdown rules unchanged. UI/desktop changes do not add process memory access, injection, packet drivers, hooks, input automation or anti-cheat interaction.
