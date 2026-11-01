//! Startup behaviour for TraderGO Universe.
//!
//! - **One instance:** starting an app that is already running (Launchpad, Dock, a double-click)
//!   focuses the open window instead of starting a second copy with its own backend and watcher.
//! - **Logs:** panics are written to the app's log folder (`~/Library/Logs/<bundle id>/` on macOS,
//!   `%LOCALAPPDATA%\<bundle id>\logs\` on Windows), never into the project.
//! - **Clear startup errors:** if the app cannot start, the reason is logged and shown in a dialog.

use std::io::Write;
use tauri::{AppHandle, Manager, Runtime};

/// Plugins every app registers first. The single-instance plugin must come before the others.
pub fn plugins<R: Runtime>(builder: tauri::Builder<R>) -> tauri::Builder<R> {
    builder.plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
        if let Some(w) = app.get_webview_window("main") {
            let _ = w.unminimize();
            let _ = w.show();
            let _ = w.set_focus();
        }
    }))
}

/// Call from `setup`: sends panics to `crash.log` in the app's log folder.
pub fn start_logging<R: Runtime>(app: &AppHandle<R>) {
    let Ok(dir) = app.path().app_log_dir() else { return };
    let _ = std::fs::create_dir_all(&dir);
    let path = dir.join("crash.log");
    let previous = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(&path) {
            let _ = writeln!(f, "{:?}: {info}", std::time::SystemTime::now());
        }
        previous(info);
    }));
}

/// Runs the app. A startup failure is logged and shown instead of the app vanishing silently.
pub fn run<R: Runtime>(builder: tauri::Builder<R>, context: tauri::Context<R>, name: &str) {
    let log_dir = startup_log_dir(&context.config().identifier);
    if let Err(e) = builder.run(context) {
        let msg = format!("{name} kunde inte starta: {e}");
        eprintln!("{msg}");
        let _ = std::fs::create_dir_all(&log_dir);
        let _ = std::fs::write(log_dir.join("startup-error.log"), &msg);
        alert(name, &msg);
        std::process::exit(1);
    }
}

/// The same folder Tauri's `app_log_dir` uses, worked out before the app exists.
fn startup_log_dir(identifier: &str) -> std::path::PathBuf {
    let var = |k: &str| std::env::var_os(k).map(std::path::PathBuf::from);
    if cfg!(target_os = "macos") {
        if let Some(h) = var("HOME") {
            return h.join("Library/Logs").join(identifier);
        }
    } else if cfg!(windows) {
        if let Some(d) = var("LOCALAPPDATA") {
            return d.join(identifier).join("logs");
        }
    }
    std::env::temp_dir().join(identifier)
}

#[cfg(target_os = "macos")]
fn alert(title: &str, msg: &str) {
    let quote = |s: &str| s.replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!("display alert \"{}\" message \"{}\" as critical", quote(title), quote(msg));
    let _ = std::process::Command::new("/usr/bin/osascript").args(["-e", &script]).status();
}

#[cfg(not(target_os = "macos"))]
fn alert(_title: &str, _msg: &str) {}
