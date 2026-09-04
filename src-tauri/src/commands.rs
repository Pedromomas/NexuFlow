use serde_json::{json, Value};
use std::{
    fs,
    path::PathBuf,
    sync::{Arc, RwLock},
    time::Duration,
};
use tauri::{AppHandle, State};
use tauri_plugin_shell::{process::CommandEvent, ShellExt};
use tokio::time::sleep;
use uuid::Uuid;

#[derive(Default)]
struct ObserverCache {
    telemetry: Option<Value>,
    games: Option<Value>,
    last_error: Option<String>,
}

#[derive(Clone, Default)]
pub struct ObserverState(Arc<RwLock<ObserverCache>>);

impl ObserverState {
    fn telemetry(&self) -> Option<Value> {
        self.0.read().ok().and_then(|cache| cache.telemetry.clone())
    }

    fn games(&self) -> Option<Value> {
        self.0.read().ok().and_then(|cache| cache.games.clone())
    }

    fn set_error(&self, message: String) {
        if let Ok(mut cache) = self.0.write() {
            cache.last_error = Some(message);
        }
    }

    fn update_snapshot(&self, value: &Value) {
        if value.get("kind").and_then(Value::as_str) != Some("snapshot") {
            return;
        }
        if let Ok(mut cache) = self.0.write() {
            if let Some(telemetry) = value.get("telemetry") {
                cache.telemetry = Some(telemetry.clone());
            }
            if let Some(games) = value.get("games") {
                cache.games = Some(games.clone());
            }
            cache.last_error = None;
        }
    }
}

fn ipc_dir() -> Result<PathBuf, String> {
    let base = std::env::temp_dir().join("NexuFlow").join("ipc");
    fs::create_dir_all(&base).map_err(|e| format!("Cannot create NexuFlow IPC directory: {e}"))?;
    Ok(base)
}

pub fn start_observer(app: AppHandle, state: ObserverState) {
    tauri::async_runtime::spawn(async move {
        let parent_pid = std::process::id().to_string();
        let snapshot_path = match ipc_dir() {
            Ok(dir) => dir.join(format!("observer-{parent_pid}.json")),
            Err(error) => {
                state.set_error(error);
                return;
            }
        };

        loop {
            let _ = fs::remove_file(&snapshot_path);
            let snapshot_arg = snapshot_path.to_string_lossy().to_string();
            let command = match app.shell().sidecar("nexus-engine") {
                Ok(command) => command.args([
                    "--observer",
                    "--parent-pid",
                    parent_pid.as_str(),
                    "--observer-file",
                    snapshot_arg.as_str(),
                ]),
                Err(error) => {
                    state.set_error(format!("Cannot resolve NexuFlow observer: {error}"));
                    sleep(Duration::from_secs(2)).await;
                    continue;
                }
            };

            match command.spawn() {
                Ok((mut rx, _child)) => {
                    let mut terminated = false;
                    while !terminated {
                        while let Ok(event) = rx.try_recv() {
                            match event {
                                CommandEvent::Terminated(_) => {
                                    terminated = true;
                                    break;
                                }
                                CommandEvent::Error(error) => state.set_error(error),
                                _ => {}
                            }
                        }
                        if terminated {
                            break;
                        }

                        match fs::read(&snapshot_path) {
                            Ok(raw) => match serde_json::from_slice::<Value>(&raw) {
                                Ok(value) => state.update_snapshot(&value),
                                Err(error) => state.set_error(format!("Observer snapshot is invalid JSON: {error}")),
                            },
                            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
                            Err(error) => state.set_error(format!("Cannot read observer snapshot: {error}")),
                        }
                        sleep(Duration::from_millis(450)).await;
                    }
                }
                Err(error) => state.set_error(format!("Cannot start NexuFlow observer: {error}")),
            }

            let _ = fs::remove_file(&snapshot_path);
            sleep(Duration::from_secs(2)).await;
        }
    });
}

async fn direct_engine(app: &AppHandle, args: &[&str]) -> Result<Value, String> {
    let output_path = ipc_dir()?.join(format!("{}.response.json", Uuid::new_v4()));
    let output_arg = output_path.to_string_lossy().to_string();
    let mut owned_args: Vec<String> = args.iter().map(|value| (*value).to_string()).collect();
    owned_args.push("--output-file".into());
    owned_args.push(output_arg);

    let output = app
        .shell()
        .sidecar("nexus-engine")
        .map_err(|e| format!("Cannot resolve NexuFlow engine sidecar: {e}"))?
        .args(owned_args)
        .output()
        .await
        .map_err(|e| format!("Cannot execute NexuFlow engine: {e}"))?;

    if !output.status.success() {
        let _ = fs::remove_file(&output_path);
        return Err("NexuFlow engine command failed.".into());
    }

    let raw = fs::read(&output_path)
        .map_err(|e| format!("Cannot read NexuFlow engine response: {e}"))?;
    let _ = fs::remove_file(&output_path);
    serde_json::from_slice::<Value>(&raw).map_err(|e| format!("Invalid engine response: {e}"))
}

#[tauri::command]
pub async fn get_telemetry(
    app: AppHandle,
    observer: State<'_, ObserverState>,
) -> Result<Value, String> {
    if let Some(value) = observer.telemetry() {
        return Ok(value);
    }
    direct_engine(&app, &["--telemetry-json"]).await
}

#[tauri::command]
pub async fn discover_games(
    app: AppHandle,
    observer: State<'_, ObserverState>,
) -> Result<Value, String> {
    if let Some(value) = observer.games() {
        return Ok(value);
    }
    direct_engine(&app, &["--discover-json"]).await
}

#[tauri::command]
pub async fn get_diagnostics(app: AppHandle) -> Result<Value, String> {
    direct_engine(&app, &["--diagnostics-json"]).await
}

fn job_paths() -> Result<(PathBuf, PathBuf), String> {
    let token = Uuid::new_v4().to_string();
    let base = std::env::temp_dir().join("NexuFlow").join("jobs");
    fs::create_dir_all(&base)
        .map_err(|e| format!("Cannot create NexuFlow temporary job directory: {e}"))?;
    Ok((
        base.join(format!("{token}.request.json")),
        base.join(format!("{token}.result.json")),
    ))
}

async fn privileged_job(app: &AppHandle, action: &str, profile: &str) -> Result<Value, String> {
    if !matches!(action, "start" | "restore") {
        return Err("Rejected unsupported privileged action".into());
    }
    if action == "start" && !matches!(profile, "ping" | "pc" | "complete" | "hardcore_safe") {
        return Err("Rejected unsupported boost profile".into());
    }

    let (request_path, result_path) = job_paths()?;
    let request = json!({
        "schema": 1,
        "action": action,
        "profile": profile,
        "requested_by": "tauri"
    });
    fs::write(
        &request_path,
        serde_json::to_vec_pretty(&request).map_err(|e| e.to_string())?,
    )
    .map_err(|e| format!("Cannot create privileged request: {e}"))?;

    let req = request_path.to_string_lossy().to_string();
    let res = result_path.to_string_lossy().to_string();
    let command = app
        .shell()
        .sidecar("nexus-engine")
        .map_err(|e| format!("Cannot resolve NexuFlow engine: {e}"))?
        .args(["--request", req.as_str(), "--result", res.as_str()]);

    let (_rx, _child) = command
        .spawn()
        .map_err(|e| format!("Cannot launch privileged helper: {e}"))?;

    // The desktop host stays unprivileged so the app can always open normally.
    // Only this narrow start/restore helper requests UAC when a system mutation
    // actually needs administrator rights. UAC is never disabled or bypassed.
    for _ in 0..600 {
        if result_path.exists() {
            let raw = fs::read(&result_path)
                .map_err(|e| format!("Cannot read helper result: {e}"))?;
            let value: Value = serde_json::from_slice(&raw)
                .map_err(|e| format!("Invalid helper result: {e}"))?;
            let _ = fs::remove_file(&request_path);
            let _ = fs::remove_file(&result_path);
            return Ok(value);
        }
        sleep(Duration::from_millis(200)).await;
    }

    let _ = fs::remove_file(&request_path);
    Err("Timed out waiting for the elevated NexuFlow engine. The UAC prompt may have been cancelled.".into())
}

#[tauri::command]
pub async fn get_gaming_health(app: AppHandle) -> Result<Value, String> {
    direct_engine(&app, &["--gaming-health-json"]).await
}

#[tauri::command]
pub async fn scan_driver_updates(app: AppHandle) -> Result<Value, String> {
    direct_engine(&app, &["--driver-scan-json"]).await
}

#[tauri::command]
pub async fn scan_connection(app: AppHandle) -> Result<Value, String> {
    direct_engine(&app, &["--connection-scan-json"]).await
}

#[tauri::command]
pub async fn run_speed_test(app: AppHandle) -> Result<Value, String> {
    direct_engine(&app, &["--speed-test-json"]).await
}

#[tauri::command]
pub async fn rank_dns(app: AppHandle) -> Result<Value, String> {
    direct_engine(&app, &["--dns-ranking-json"]).await
}

#[tauri::command]
pub async fn open_pc_settings(app: AppHandle, section: String) -> Result<Value, String> {
    if !["game_mode", "captures", "graphics", "startup", "storage", "power", "network"].contains(&section.as_str()) {
        return Err("Destino de ajustes não permitido".into());
    }
    direct_engine(&app, &["--open-pc-settings", section.as_str()]).await
}

#[tauri::command]
pub async fn open_driver_updates(app: AppHandle) -> Result<Value, String> {
    direct_engine(&app, &["--open-driver-updates-json"]).await
}

#[tauri::command]
pub async fn get_history(app: AppHandle) -> Result<Value, String> {
    direct_engine(&app, &["--history-json"]).await
}

#[tauri::command]
pub async fn get_investigator(app: AppHandle) -> Result<Value, String> {
    direct_engine(&app, &["--investigator-json"]).await
}

#[tauri::command]
pub async fn sign_session_report(app: AppHandle, report: Value) -> Result<Value, String> {
    let raw = serde_json::to_vec(&report).map_err(|e| format!("Invalid report: {e}"))?;
    if raw.len() > 256 * 1024 {
        return Err("Session report exceeds the signing size limit".into());
    }
    let request_path = ipc_dir()?.join(format!("{}.report.json", Uuid::new_v4()));
    fs::write(&request_path, raw).map_err(|e| format!("Cannot create report request: {e}"))?;
    let request_arg = request_path.to_string_lossy().to_string();
    let result = direct_engine(&app, &["--sign-report-file", request_arg.as_str()]).await;
    let _ = fs::remove_file(&request_path);
    result
}

#[tauri::command]
pub async fn get_recovery_status(app: AppHandle) -> Result<Value, String> {
    direct_engine(&app, &["--recovery-json"]).await
}

#[tauri::command]
pub async fn get_anti_cheat_status(app: AppHandle, game_id: Option<String>) -> Result<Value, String> {
    match game_id {
        Some(id) if !id.trim().is_empty() => direct_engine(&app, &["--anti-cheat-json", id.as_str()]).await,
        _ => direct_engine(&app, &["--anti-cheat-json"]).await,
    }
}

#[tauri::command]
pub async fn get_route_diagnostics(app: AppHandle, target: String) -> Result<Value, String> {
    direct_engine(&app, &["--route-diagnostics-json", target.as_str()]).await
}

#[tauri::command]
pub fn updater_configured() -> bool {
    cfg!(feature = "signed-updater")
}

#[tauri::command]
pub async fn start(app: AppHandle, profile: String, desktop: State<'_, crate::desktop::DesktopState>) -> Result<Value, String> {
    let _operation = desktop.operations.lock().await;
    if desktop.exiting.load(std::sync::atomic::Ordering::SeqCst) {
        return Err("NexuFlow está encerrando; aguarde a restauração.".into());
    }
    privileged_job(&app, "start", &profile).await
}

#[tauri::command]
pub async fn stop(app: AppHandle, _profile: String, desktop: State<'_, crate::desktop::DesktopState>) -> Result<Value, String> {
    let _operation = desktop.operations.lock().await;
    // Stopping only requests the already-elevated daemon to rollback and exit.
    // It cannot apply new privileged changes, so another UAC prompt is not
    // necessary or desirable.
    direct_engine(&app, &["--stop-signal-json"]).await
}

#[tauri::command]
pub async fn restore(app: AppHandle, profile: String, desktop: State<'_, crate::desktop::DesktopState>) -> Result<Value, String> {
    let _operation = desktop.operations.lock().await;
    restore_engine(&app, &profile).await
}

pub async fn restore_engine(app: &AppHandle, profile: &str) -> Result<Value, String> {
    // Fast path: if the elevated daemon is still alive, ask it to perform its
    // own rollback with no second UAC prompt. A stale snapshot with no daemon
    // still requires Windows elevation because actual privileged restoration
    // may be necessary.
    let quick = direct_engine(&app, &["--stop-signal-json"]).await?;
    if quick["data"]["stopped"].as_bool() != Some(true) {
        return Err("O motor ainda está finalizando o rollback. Aguarde e tente novamente.".into());
    }
    let pending = quick
        .get("data")
        .and_then(|value| value.get("restore_pending"))
        .and_then(Value::as_bool)
        .unwrap_or(true);
    if !pending {
        return Ok(json!({
            "ok": true,
            "action": "restore",
            "message": "Rollback concluído sem nova solicitação de UAC.",
            "data": quick.get("data").cloned().unwrap_or(Value::Null)
        }));
    }
    let restored = privileged_job(&app, "restore", &profile).await?;
    if restored["ok"].as_bool() != Some(true) { return Ok(restored); }
    // Re-read the daemon and snapshot state instead of trusting a launch result.
    direct_engine(&app, &["--stop-signal-json"]).await
}
