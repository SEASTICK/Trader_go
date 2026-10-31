// Hide the console window on Windows release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod activity;
mod db;
mod project_map;
mod safety;
mod updater;

use activity::{Activity, Counts};
use rusqlite::Connection;
use serde::Serialize;
use std::sync::Mutex;
use tauri::{Manager, State};

pub struct AppState {
    pub db: Mutex<Connection>,
    pub activity: Activity,
}

#[derive(Serialize)]
struct AppInfo {
    version: String,
    mode: &'static str,
    data_dir: String,
    schema: usize,
    auto_download: bool,
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
        auto_download: db::get_setting(&conn, "auto_download")
            .map_err(|e| e.to_string())?
            .as_deref()
            != Some("false"),
    })
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
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let data_dir = app.path().app_data_dir()?;
            let path = data_dir.join("tradergo.db");
            let conn = db::open(&path).map_err(|e| {
                // Surface the reason instead of starting with an empty or half-migrated store.
                let msg = format!(
                    "Trader_go kunde inte öppna sin databas på {}:\n\n{e}",
                    path.display()
                );
                eprintln!("{msg}");
                msg
            })?;
            let map_root = db::get_setting(&conn, "project_root")
                .ok()
                .flatten()
                .map(std::path::PathBuf::from);
            app.manage(project_map::MapService::start(
                app.handle().clone(),
                data_dir,
                map_root,
            ));
            app.manage(AppState {
                db: Mutex::new(conn),
                activity: Activity::default(),
            });
            app.manage(updater::UpdateState::default());
            tauri::async_runtime::spawn(updater::startup(app.handle().clone()));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            app_info,
            set_setting,
            add_paper_trade,
            list_paper_trades,
            start_activity,
            stop_activity,
            updater::update_status,
            updater::check_for_update,
            updater::download_update,
            updater::install_update,
            project_map::map_info,
            project_map::map_choose_root,
            project_map::map_refresh,
            project_map::map_load,
            project_map::map_save,
            project_map::map_save_copy,
            project_map::map_export,
            project_map::map_preview,
            project_map::map_reveal,
            project_map::map_open_obsidian,
        ])
        .run(tauri::generate_context!())
        .expect("fel när Trader_go startades");
}
