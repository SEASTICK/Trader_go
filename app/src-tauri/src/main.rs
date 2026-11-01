// Förhindrar extra konsolfönster på Windows i release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// Trader_go: forskning och papper. Marknadsdatan är publik och bara läses (src/market); inga nycklar,
// inga konton, inga order.
mod market;

use std::time::Duration;
use tauri::{Emitter, Manager};

fn main() {
    let app = tauri::Builder::default()
        // Ett exemplar: en andra start visar det öppna fönstret i stället för att starta en andra insamlare.
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(w) = app.get_webview_window("main") {
                let _ = w.unminimize();
                let _ = w.show();
                let _ = w.set_focus();
            }
        }))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            let dir = app.path().app_data_dir()?.join("market");
            let handle = app.handle().clone();
            let collector = market::Collector::start(dir, Box::new(move |s| {
                let _ = handle.emit(market::STATUS_EVENT, s);
            }));
            app.manage(collector);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![market::market_status])
        .build(tauri::generate_context!())
        .expect("fel när Trader_go startades");
    app.run(|app, event| {
        if let tauri::RunEvent::Exit = event {
            // Stäng anslutningen och låt sista skrivningen bli klar innan processen avslutas.
            app.state::<market::Collector>().stop(Duration::from_secs(3));
        }
    });
}
