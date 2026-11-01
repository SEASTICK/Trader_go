// Hide the console window on Windows release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod activity;
mod db;
mod market;
mod safety;

use activity::{Activity, Counts};
use rusqlite::Connection;
use serde::Serialize;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::Duration;
use tauri::{Emitter, Manager, State};

pub struct AppState {
    pub db: Mutex<Connection>,
    pub db_path: PathBuf,
    pub activity: Activity,
}

#[derive(Serialize)]
struct AppInfo {
    version: String,
    mode: &'static str,
    data_dir: String,
    schema: usize,
}

#[tauri::command]
fn app_info(app: tauri::AppHandle, state: State<'_, AppState>) -> Result<AppInfo, String> {
    let conn = state.db.lock().unwrap();
    Ok(AppInfo {
        version: app.package_info().version.to_string(),
        mode: safety::TRADING_MODE,
        data_dir: app
            .path()
            .app_data_dir()
            .map_err(|e| e.to_string())?
            .display()
            .to_string(),
        schema: db::schema_version(&conn).map_err(|e| e.to_string())?,
    })
}

/// Called by the frontend updater right before it downloads and installs. Refuses while a
/// paper session or backtest runs, then backs up the database so an update can be undone.
#[tauri::command]
fn prepare_update_install(state: State<'_, AppState>) -> Result<String, String> {
    state.activity.ensure_idle()?;
    let conn = state.db.lock().unwrap();
    db::backup_before_update(&conn, &state.db_path)
        .map(|p| p.display().to_string())
        .map_err(|e| format!("Kunde inte säkerhetskopiera databasen före uppdateringen: {e}"))
}

#[tauri::command]
fn set_setting(key: String, value: String, state: State<'_, AppState>) -> Result<(), String> {
    safety::check_setting(&key, &value)?;
    db::put_setting(&state.db.lock().unwrap(), &key, &value).map_err(|e| e.to_string())
}

#[tauri::command]
fn add_paper_trade(
    symbol: String,
    side: String,
    quantity: f64,
    entry_price: f64,
    state: State<'_, AppState>,
) -> Result<i64, String> {
    safety::check_paper_trade(&symbol, &side, quantity, entry_price)?;
    let conn = state.db.lock().unwrap();
    db::insert_paper_trade(&conn, symbol.trim(), &side, quantity, entry_price)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn list_paper_trades(state: State<'_, AppState>) -> Result<Vec<db::PaperTrade>, String> {
    db::list_paper_trades(&state.db.lock().unwrap(), 50).map_err(|e| e.to_string())
}

#[tauri::command]
fn start_activity(kind: String, state: State<'_, AppState>) -> Result<Counts, String> {
    state.activity.start(&kind)
}

#[tauri::command]
fn stop_activity(kind: String, state: State<'_, AppState>) -> Result<Counts, String> {
    state.activity.stop(&kind)
}

fn main() {
    let app = tauri::Builder::default()
        // One instance: a second launch shows the open window instead of starting a second
        // market-data collector (src/market).
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
            let path = app.path().app_data_dir()?.join("tradergo.db");
            let conn = db::open(&path).map_err(|e| {
                // Surface the reason instead of starting with an empty or half-migrated store.
                let msg = format!(
                    "Trader_go kunde inte öppna sin databas på {}:\n\n{e}",
                    path.display()
                );
                eprintln!("{msg}");
                msg
            })?;
            app.manage(AppState {
                db: Mutex::new(conn),
                db_path: path,
                activity: Activity::default(),
            });
            // Public market data only (no keys, no account, no orders); see docs/marknadsdata.md.
            let dir = app.path().app_data_dir()?.join("market");
            let status = app.handle().clone();
            let bars = app.handle().clone();
            let collector = market::Collector::start(
                dir,
                Box::new(move |s| {
                    let _ = status.emit(market::STATUS_EVENT, s);
                }),
                Box::new(move |b| {
                    let _ = bars.emit(market::BAR_EVENT, b);
                }),
            );
            app.manage(collector);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            app_info,
            set_setting,
            add_paper_trade,
            list_paper_trades,
            start_activity,
            stop_activity,
            prepare_update_install,
            market::market_status,
            market::market_series,
            market::market_bars,
        ])
        .build(tauri::generate_context!())
        .expect("fel när Trader_go startades");
    app.run(|app, event| {
        if let tauri::RunEvent::Exit = event {
            // Close the market-data connection and let the last write finish before exiting.
            app.state::<market::Collector>()
                .stop(Duration::from_secs(3));
        }
    });
}
