from pathlib import Path

from nexus_engine.state import stop_file


ROOT = Path(__file__).resolve().parents[2]


def test_release_tauri_host_is_window_subsystem():
    main_rs = (ROOT / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")
    assert 'windows_subsystem = "windows"' in main_rs


def test_packaged_engine_is_windowless():
    build_script = (ROOT / "scripts" / "build-engine.ps1").read_text(encoding="utf-8")
    spec = (ROOT / "nexus-engine.spec").read_text(encoding="utf-8")
    assert "--windowed" in build_script
    assert "console=False" in spec


def test_stop_channel_is_one_way_user_control_path():
    path = stop_file()
    assert path.name == "stop.request"
    assert path.parent.name == "control"
    assert path.parent.parent.name == "NexuFlow"


def test_tauri_stop_does_not_spawn_new_privileged_job():
    commands = (ROOT / "src-tauri" / "src" / "commands.rs").read_text(encoding="utf-8")
    start = commands.index("pub async fn stop")
    restore = commands.index("pub async fn restore", start)
    stop_block = commands[start:restore]
    assert 'direct_engine(&app, &["--stop-signal-json"])' in stop_block
    assert "privileged_job" not in stop_block


def test_ui_has_persisted_accessibility_surfaces():
    component = (ROOT / "src" / "app" / "app.component.ts").read_text(encoding="utf-8")
    template = (ROOT / "src" / "app" / "app.component.html").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "styles.css").read_text(encoding="utf-8")
    assert "nexuflow_ui_preferences_v1" in component
    assert "Alto contraste" in template
    assert "TAMANHO DO TEXTO" in template
    assert "prefers-reduced-motion" in styles
    assert "hotbar" in template


def test_142_ui_exposes_only_four_plain_language_objectives():
    component = (ROOT / "src" / "app" / "app.component.ts").read_text(encoding="utf-8")
    template = (ROOT / "src" / "app" / "app.component.html").read_text(encoding="utf-8")
    assert "Vanguard Safe +" in component
    assert "O QUE ESTE MODO FAZ" in template
    assert "ATIVO E PERMITIDO" in template
    assert "BLOQUEADO PELO SAFE CORE" in template
    assert "setProfile('roblox')" not in template
    assert "setProfile('aggressive')" not in template
    assert "setProfile('auto')" not in template
    assert template.count("class=\"profile-card") == 4
    assert "Saiba mais" in template
    assert "em palavras simples" in component
    assert "Jogos monitorados" in template
    for game_id in ("lol", "valorant", "cs2", "roblox", "generic"):
        assert (ROOT / "public" / "game-icons" / f"{game_id}.svg").is_file()


def test_142_requests_windows_elevation_once_at_app_launch():
    manifest = (ROOT / "src-tauri" / "app.manifest").read_text(encoding="utf-8")
    build_rs = (ROOT / "src-tauri" / "build.rs").read_text(encoding="utf-8")
    dev_script = (ROOT / "scripts" / "dev.ps1").read_text(encoding="utf-8")
    commands = (ROOT / "src-tauri" / "src" / "commands.rs").read_text(encoding="utf-8")
    assert 'level="requireAdministrator"' in manifest
    assert 'include_str!("app.manifest")' in build_rs
    assert "-Verb RunAs" in dev_script
    start = commands.index("pub async fn start")
    stop = commands.index("pub async fn stop", start)
    assert "privileged_job" in commands[start:stop]


def test_cs2_icon_is_identified_and_no_longer_uses_the_lightning_mark():
    icon = (ROOT / "public" / "game-icons" / "cs2.svg").read_text(encoding="utf-8")
    assert 'aria-label="Counter-Strike 2"' in icon
    assert "cs2g" in icon
    assert "M39 18h12l-9 13" not in icon
