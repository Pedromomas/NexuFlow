mod commands;
mod desktop;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let observer = commands::ObserverState::default();
    let observer_for_setup = observer.clone();

    let builder = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init());

    // Do not initialize the updater with missing/placeholder credentials: the
    // official plugin rejects an absent configuration before the window opens.
    // The release feature is enabled only together with the real HTTPS endpoint
    // and embedded public key described in docs/UPDATER_1.8.md.
    #[cfg(feature = "signed-updater")]
    let builder = builder.plugin(tauri_plugin_updater::Builder::new().build());

    builder
        .manage(observer)
        .manage(desktop::DesktopState::default())
        .setup(move |app| {
            desktop::install_tray(app.handle())?;
            commands::start_observer(app.handle().clone(), observer_for_setup.clone());
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                desktop::request_shutdown(window.app_handle().clone());
            }
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_telemetry,
            commands::discover_games,
            commands::get_diagnostics,
            commands::get_gaming_health,
            commands::scan_driver_updates,
            commands::scan_connection,
            commands::run_speed_test,
            commands::rank_dns,
            commands::open_pc_settings,
            commands::open_driver_updates,
            commands::get_history,
            commands::get_investigator,
            commands::sign_session_report,
            commands::get_recovery_status,
            commands::get_anti_cheat_status,
            commands::get_route_diagnostics,
            commands::updater_configured,
            commands::start,
            commands::stop,
            commands::restore,
            desktop::set_artwork_fullscreen
        ])
        .run(tauri::generate_context!())
        .expect("failed to run NexuFlow");
}
