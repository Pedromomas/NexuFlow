from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOTS = (
    ROOT / "engine" / "src" / "nexus_engine",
    ROOT / "app" / "modules",
    ROOT / "src-tauri" / "src",
)
FORBIDDEN_RUNTIME_SYMBOLS = (
    "ReadProcessMemory",
    "WriteProcessMemory",
    "NtReadVirtualMemory",
    "NtWriteVirtualMemory",
    "VirtualAllocEx",
    "CreateRemoteThread",
    "SetWindowsHookEx",
    "SendInput",
    "WinDivert",
    "Npcap",
    "SharpPcap",
    "Detours",
)


def test_runtime_has_no_injection_memory_hook_or_packet_driver_symbols():
    violations: list[str] = []
    for base in RUNTIME_ROOTS:
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".rs", ".toml", ".json"}:
                continue
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for symbol in FORBIDDEN_RUNTIME_SYMBOLS:
                if symbol in text:
                    violations.append(f"{path.relative_to(ROOT)}: {symbol}")
    assert not violations, "forbidden anti-cheat-sensitive runtime surface:\n" + "\n".join(violations)


def test_source_package_contains_no_kernel_or_asi_payloads():
    forbidden = []
    ignored = {"node_modules", "target", ".venv", "build", "dist"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".sys", ".asi"}:
            continue
        if ignored.intersection(path.parts):
            continue
        forbidden.append(str(path.relative_to(ROOT)))
    assert not forbidden


def test_cs2_trusted_mode_override_not_present_in_launch_code():
    candidates = list((ROOT / "src-tauri").rglob("*.rs"))
    candidates += list((ROOT / "src-tauri").rglob("*.json"))
    candidates += list((ROOT / "scripts").rglob("*.ps1"))
    candidates += [ROOT / "package.json"]
    offenders = []
    for path in candidates:
        if "target" in path.parts or not path.exists():
            continue
        if "allow_third_party_software" in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders


def test_no_runtime_module_spawns_powershell_outside_central_guard():
    runtime = ROOT / "engine" / "src" / "nexus_engine"
    offenders = []
    for path in runtime.rglob("*.py"):
        if path.name == "winexec.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if 'subprocess.run(["powershell' in text or 'subprocess.popen(["powershell' in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders


def test_tauri_public_profile_boundary_rejects_internal_profiles():
    commands = (ROOT / "src-tauri" / "src" / "commands.rs").read_text(encoding="utf-8")
    public_line = next(line for line in commands.splitlines() if 'action == "start" && !matches!' in line)
    for profile in ("ping", "pc", "complete", "hardcore_safe"):
        assert f'"{profile}"' in public_line
    for internal in ("aggressive", "riot_safe", "valve_safe", "unknown_safe", "protected_safe"):
        assert f'"{internal}"' not in public_line


def test_driver_center_does_not_install_or_download_drivers_silently():
    module = (ROOT / "engine" / "src" / "nexus_engine" / "hardware" / "driver_center.py").read_text(encoding="utf-8").casefold()
    for forbidden in ("createupdateinstaller", "createdownloader", "pnputil /add-driver", "pnputil /delete-driver"):
        assert forbidden not in module
    assert "ms-settings:windowsupdate-optionalupdates" in module
