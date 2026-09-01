# NexuFlow 1.4.2 — Clear Boost

Clear Boost keeps only four user-facing choices: Ping, PC, Complete and Hardcore Safe. Roblox Profile, Aggressive and automatic anti-cheat profiles no longer appear as competing buttons. Game-specific safety is an automatic overlay and every mode now has a plain-language “Saiba mais” explanation.

The supported-games screen is explicitly a compatibility catalog, not a complete launcher library. It reports how many validated games exist and how many were actually found on the current PC. Counter-Strike 2 receives a new local icon.

On Windows, the desktop host requests administrator permission once at application launch. Child engine processes inherit that permission, avoiding a new UAC prompt on each BOOST while preserving the Windows security boundary. Unsigned development builds can still display “Unknown publisher”; only a valid Authenticode certificate changes publisher trust.

Vanguard Boost separates the user's objective (Ping, PC, Complete or Hardcore Safe) from the automatic safety overlay. League of Legends and VALORANT display Vanguard Safe + Ping/PC/Complete; CS2 displays the equivalent Valve Safe mode. EAC/BattlEye and unknown games remain fail-closed. Protected Ping is diagnostic-only during play, while protected PC may use a temporary global Windows power plan without opening or changing the game process.

The Protected Session Shield rolls back an active mutable session before a protected runtime takes over. Pre-flight 2.0 is read-only and reports Secure Boot, TPM, VBS/HVCI, test signing, kernel debugging, integrity checks, DEP and Driver Verifier where Windows exposes reliable state.

Remote policy is tracking-free HTTPS, signed, expiring, monotonic and disable-only. It cannot execute commands, enable features, authorize process closure or add mutations. Invalid policy is rejected.

Release gates include Python/web tests, the No-Driver Contract, forbidden anti-cheat surface audit, CycloneDX SBOM, SHA-256 manifest and ZIP hashing. Privacy defaults to local history, no analytics SDK, no device fingerprint and sanitized report export.
