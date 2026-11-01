//! TraderGO Universe: a read-only map of the TraderGO project folder.
//!
//! Universe finds the project folder by itself on each computer, so nothing depends on one
//! person's user name or disk layout. It only reads the folder; the map, layout and the chosen
//! folder are stored in the app's own data folder.

use crate::project_map::{self, MapService};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use tauri::{AppHandle, Emitter, Manager, Wry};

/// Folder names tried under the home folder, in order (macOS, Windows and Linux habits).
const CANDIDATES: &[&str] = &[
    "Documents/GitHub/Trader_go",
    "GitHub/Trader_go",
    "Developer/Trader_go",
    "Projects/Trader_go",
    "Documents/Trader_go",
    "source/repos/Trader_go",
    "code/Trader_go",
    "src/Trader_go",
];

#[derive(Serialize, Deserialize, Default)]
struct Settings {
    /// The folder the user picked. Machine-specific, so it lives in app data, never in Git.
    custom_root: Option<PathBuf>,
}

fn settings_path(app: &AppHandle) -> Result<PathBuf, String> {
    Ok(app.path().app_data_dir().map_err(|e| e.to_string())?.join("universe-settings.json"))
}

fn load_settings(app: &AppHandle) -> Settings {
    settings_path(app)
        .ok()
        .and_then(|p| std::fs::read(p).ok())
        .and_then(|b| serde_json::from_slice(&b).ok())
        .unwrap_or_default()
}

pub fn save_custom_root(app: &AppHandle, root: Option<&Path>) -> Result<(), String> {
    let path = settings_path(app)?;
    std::fs::create_dir_all(path.parent().unwrap()).map_err(|e| e.to_string())?;
    let s = Settings { custom_root: root.map(Path::to_path_buf) };
    project_map::engine::atomic_write(&path, &serde_json::to_vec_pretty(&s).unwrap()).map_err(|e| e.to_string())
}

/// A TraderGO checkout: the project rules plus the Universe app folder.
pub fn is_project_root(p: &Path) -> bool {
    p.join("CLAUDE.md").is_file() && p.join("apps").join("trader-go-universe").is_dir()
}

#[derive(Serialize, Clone)]
pub struct Discovery {
    root: Option<String>,
    /// searching | saved | env | dev | found | none
    source: &'static str,
    tried: Vec<String>,
}

/// Where the project folder is, and how it was found.
fn discover(app: &AppHandle) -> (Option<PathBuf>, Discovery) {
    let mut tried = Vec::new();
    let pick = |p: PathBuf, source: &'static str, tried: &mut Vec<String>| {
        tried.push(p.display().to_string());
        is_project_root(&p).then_some((p, source))
    };
    let found = load_settings(app)
        .custom_root
        .and_then(|p| pick(p, "saved", &mut tried))
        .or_else(|| std::env::var_os("TRADERGO_ROOT").and_then(|v| pick(PathBuf::from(v), "env", &mut tried)))
        .or_else(|| {
            // `npm run universe` from a checkout: the folder three levels above this crate.
            if cfg!(debug_assertions) {
                let dev = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..");
                dev.canonicalize().ok().and_then(|p| pick(p, "dev", &mut tried))
            } else {
                None
            }
        })
        .or_else(|| {
            let home = app.path().home_dir().ok()?;
            CANDIDATES.iter().find_map(|c| pick(home.join(c), "found", &mut tried))
        });
    let d = Discovery {
        root: found.as_ref().map(|(p, _)| p.display().to_string()),
        source: found.as_ref().map_or("none", |(_, s)| *s),
        tried,
    };
    (found.map(|(p, _)| p), d)
}

pub fn setup(builder: tauri::Builder<Wry>) -> tauri::Builder<Wry> {
    builder
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            crate::desktop::start_logging(app.handle());
            let handle = app.handle().clone();
            app.manage(Mutex::new(Discovery { root: None, source: "searching", tried: Vec::new() }));
            let meta = app.path().app_data_dir()?.join("map");
            app.manage(MapService::start(handle.clone(), meta, None));
            // Looking in ~/Documents can make macOS ask for permission and wait for the answer, so
            // the search runs after the window is up instead of holding up startup.
            std::thread::spawn(move || {
                let (root, discovery) = discover(&handle);
                *handle.state::<Mutex<Discovery>>().lock().unwrap() = discovery.clone();
                if let Some(root) = root {
                    handle.state::<MapService>().use_root(root);
                }
                let _ = handle.emit("universe-discovery", discovery);
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
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
            universe_discovery,
        ])
}

/// How Universe found the project folder (for the diagnostics panel).
#[tauri::command]
fn universe_discovery(d: tauri::State<'_, Mutex<Discovery>>) -> Discovery {
    d.lock().unwrap().clone()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn recognises_a_checkout_and_nothing_else() {
        let dir = tempfile::tempdir().unwrap();
        assert!(!is_project_root(dir.path()));
        std::fs::write(dir.path().join("CLAUDE.md"), "rules").unwrap();
        assert!(!is_project_root(dir.path()));
        std::fs::create_dir_all(dir.path().join("apps/trader-go-universe")).unwrap();
        assert!(is_project_root(dir.path()));
    }

    #[test]
    fn this_checkout_is_found_in_development() {
        let dev = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..").canonicalize().unwrap();
        assert!(is_project_root(&dev), "{} should be the project root", dev.display());
    }
}
