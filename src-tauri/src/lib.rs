mod commands;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let observer = commands::ObserverState::default();
    let observer_for_setup = observer.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(observer)
        .setup(move |app| {
            commands::start_observer(app.handle().clone(), observer_for_setup.clone());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_telemetry,
            commands::discover_games,
            commands::get_diagnostics,
            commands::get_gaming_health,
            commands::scan_driver_updates,
            commands::open_driver_updates,
            commands::get_history,
            commands::get_recovery_status,
            commands::get_anti_cheat_status,
            commands::get_route_diagnostics,
            commands::start,
            commands::stop,
            commands::restore
        ])
        .run(tauri::generate_context!())
        .expect("failed to run NexuFlow");
}
