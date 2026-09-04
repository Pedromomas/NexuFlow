use std::sync::atomic::{AtomicBool, Ordering};
use tauri::{menu::{Menu, MenuItem}, tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent}, AppHandle, Emitter, Manager};
use tokio::sync::Mutex;

#[derive(Default)]
pub struct DesktopState {
    pub exiting: AtomicBool,
    pub operations: Mutex<()>,
}

fn show_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

pub fn install_tray(app: &AppHandle) -> tauri::Result<()> {
    let show = MenuItem::with_id(app, "show", "Abrir NexuFlow", true, None::<&str>)?;
    let hide = MenuItem::with_id(app, "hide", "Ocultar na bandeja", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "Sair — restaurar e encerrar", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&show, &hide, &quit])?;
    let mut tray = TrayIconBuilder::with_id("nexuflow")
        .tooltip("NexuFlow — abrir, ocultar ou encerrar")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "show" => show_window(app),
            "hide" => { if let Some(window) = app.get_webview_window("main") { let _ = window.hide(); } },
            "quit" => request_shutdown(app.clone()),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if matches!(event, TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. }) {
                show_window(tray.app_handle());
            }
        });
    if let Some(icon) = app.default_window_icon() { tray = tray.icon(icon.clone()); }
    tray.build(app)?;
    Ok(())
}

pub fn request_shutdown(app: AppHandle) {
    if app.state::<DesktopState>().exiting.swap(true, Ordering::SeqCst) { return; }
    tauri::async_runtime::spawn(async move {
        let state = app.state::<DesktopState>();
        // Wait for an in-flight start/stop: never race the daemon's initial setup.
        let _operation = state.operations.lock().await;
        let _ = app.emit("desktop-status", "Restaurando ajustes antes de encerrar…");
        if let Some(window) = app.get_webview_window("main") {
            let _ = window.set_title("NexuFlow — restaurando antes de sair…");
        }
        match crate::commands::restore_engine(&app, "hardcore_safe").await {
            Ok(value) if shutdown_confirmed(&value) => {
                app.exit(0);
            }
            result => {
                let detail = match result {
                    Err(error) => error,
                    Ok(_) => "O motor ainda não confirmou a restauração.".to_string(),
                };
                state.exiting.store(false, Ordering::SeqCst);
                let _ = app.emit("desktop-status", format!("Não foi possível encerrar: {detail} Use Restaurar tudo e tente novamente."));
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.set_title("NexuFlow — restauração pendente; tente sair novamente");
                }
                show_window(&app);
            }
        }
    });
}

fn shutdown_confirmed(value: &serde_json::Value) -> bool {
    value["ok"].as_bool() == Some(true)
        && value["data"]["stopped"].as_bool() == Some(true)
        && value["data"]["restore_pending"].as_bool() == Some(false)
}

#[tauri::command]
pub fn set_artwork_fullscreen(window: tauri::WebviewWindow, enabled: bool) -> Result<bool, String> {
    let previous = window.is_fullscreen().map_err(|error| error.to_string())?;
    window.set_fullscreen(enabled).map_err(|error| error.to_string())?;
    Ok(previous)
}

#[cfg(test)]
mod tests {
    use super::shutdown_confirmed;
    use serde_json::json;

    #[test]
    fn exit_requires_explicit_stopped_and_restored_confirmation() {
        assert!(shutdown_confirmed(&json!({"ok":true,"data":{"stopped":true,"restore_pending":false}})));
        for response in [
            json!({"ok":true}),
            json!({"ok":false,"data":{"stopped":true,"restore_pending":false}}),
            json!({"ok":true,"data":{"stopped":false,"restore_pending":false}}),
            json!({"ok":true,"data":{"stopped":true,"restore_pending":true}}),
        ] { assert!(!shutdown_confirmed(&response)); }
    }
}
