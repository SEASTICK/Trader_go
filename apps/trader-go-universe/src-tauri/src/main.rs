// Förhindrar extra konsolfönster på Windows i release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// TraderGO Universe: en karta över projektmappen som bara läser. Ingen orderkod, inga nycklar,
// ingen nätverkskod utöver uppdateringskontrollen.
mod desktop;
mod project_map;
mod universe;

fn main() {
    let builder = desktop::plugins(tauri::Builder::default())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init());
    desktop::run(universe::setup(builder), tauri::generate_context!(), "TraderGO Universe");
}
