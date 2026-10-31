// Förhindrar extra konsolfönster på Windows i release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("fel när Trader_go startades");
}
