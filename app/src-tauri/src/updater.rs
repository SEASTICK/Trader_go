//! In-app updates via tauri-plugin-updater. The plugin downloads `latest.json` from GitHub
//! Releases, and every package is checked against the Ed25519 public key in `tauri.conf.json`
//! before it can be installed. Installation waits until no paper session or backtest runs.

use crate::AppState;
use serde::Serialize;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use tauri::{AppHandle, Emitter, Manager, State};
use tauri_plugin_updater::{Update, UpdaterExt};

pub const STATUS_EVENT: &str = "update-status";

#[derive(Default)]
pub struct UpdateState {
    available: Mutex<Option<Update>>,
    ready: Mutex<Option<(Update, Vec<u8>)>>,
    downloading: AtomicBool,
    last: Mutex<Option<Status>>,
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct Status {
    /// checking | none | available | downloading | ready | error
    pub state: &'static str,
    pub current: String,
    pub version: Option<String>,
    pub notes: Option<String>,
    pub date: Option<String>,
    pub downloaded: u64,
    pub total: Option<u64>,
    pub message: Option<String>,
}

fn emit(app: &AppHandle, status: Status) -> Status {
    *app.state::<UpdateState>().last.lock().unwrap() = Some(status.clone());
    let _ = app.emit(STATUS_EVENT, status.clone());
    status
}

fn base(app: &AppHandle, state: &'static str) -> Status {
    Status {
        state,
        current: app.package_info().version.to_string(),
        ..Default::default()
    }
}

fn with_update(mut s: Status, u: &Update) -> Status {
    s.version = Some(u.version.clone());
    s.notes = u.body.clone();
    s.date = u.date.map(|d| d.to_string());
    s
}

/// Turns plugin errors into something a user can act on.
pub fn friendly(err: &str) -> String {
    let e = err.to_lowercase();
    if e.contains("signature") || e.contains("minisign") || e.contains("pubkey") {
        "The downloaded update failed signature verification and was discarded. Nothing was installed."
            .into()
    } else if e.contains("dns")
        || e.contains("connect")
        || e.contains("network")
        || e.contains("timed out")
    {
        "Could not reach the update server. You may be offline; TraderGO keeps working with local data."
            .into()
    } else if e.contains("404") || e.contains("not found") {
        "No published release was found on the update server yet.".into()
    } else {
        format!("Update failed: {err}")
    }
}

fn auto_download_enabled(app: &AppHandle) -> bool {
    let state = app.state::<AppState>();
    let conn = state.db.lock().unwrap();
    crate::db::get_setting(&conn, "auto_download")
        .ok()
        .flatten()
        .as_deref()
        != Some("false")
}

pub async fn check(app: &AppHandle) -> Status {
    emit(app, base(app, "checking"));
    let result = match app.updater() {
        Ok(u) => u.check().await.map_err(|e| e.to_string()),
        Err(e) => Err(e.to_string()),
    };
    match result {
        Ok(Some(update)) => {
            let status = emit(app, with_update(base(app, "available"), &update));
            *app.state::<UpdateState>().available.lock().unwrap() = Some(update);
            status
        }
        Ok(None) => emit(app, base(app, "none")),
        Err(e) => {
            let mut s = base(app, "error");
            s.message = Some(friendly(&e));
            emit(app, s)
        }
    }
}

pub async fn download(app: &AppHandle) -> Result<(), String> {
    let us = app.state::<UpdateState>();
    let Some(update) = us.available.lock().unwrap().clone() else {
        return Err("No update to download. Check for updates first.".into());
    };
    if us.downloading.swap(true, Ordering::SeqCst) {
        return Ok(());
    }
    let mut downloaded = 0u64;
    let progress_app = app.clone();
    let progress_update = update.clone();
    let result = update
        .download(
            move |chunk, total| {
                downloaded += chunk as u64;
                let mut s = with_update(base(&progress_app, "downloading"), &progress_update);
                s.downloaded = downloaded;
                s.total = total;
                emit(&progress_app, s);
            },
            || {},
        )
        .await;
    us.downloading.store(false, Ordering::SeqCst);

    match result {
        Ok(bytes) => {
            let mut s = with_update(base(app, "ready"), &update);
            if let Err(why) = app.state::<AppState>().activity.ensure_idle() {
                s.message = Some(why);
            }
            *us.ready.lock().unwrap() = Some((update, bytes));
            emit(app, s);
            Ok(())
        }
        Err(e) => {
            let msg = friendly(&e.to_string());
            let mut s = with_update(base(app, "error"), &update);
            s.message = Some(msg.clone());
            emit(app, s);
            Err(msg)
        }
    }
}

/// Startup: check, and download in the background if the user allows it.
pub async fn startup(app: AppHandle) {
    if check(&app).await.state == "available" && auto_download_enabled(&app) {
        let _ = download(&app).await;
    }
}

#[tauri::command]
pub async fn check_for_update(app: AppHandle) -> Result<Status, String> {
    let status = check(&app).await;
    if status.state == "available" && auto_download_enabled(&app) {
        let bg = app.clone();
        tauri::async_runtime::spawn(async move {
            let _ = download(&bg).await;
        });
    }
    Ok(status)
}

#[tauri::command]
pub async fn download_update(app: AppHandle) -> Result<(), String> {
    download(&app).await
}

/// Last status, for a window that subscribed after the startup check already ran.
#[tauri::command]
pub fn update_status(app: AppHandle, us: State<'_, UpdateState>) -> Status {
    us.last
        .lock()
        .unwrap()
        .clone()
        .unwrap_or_else(|| base(&app, "none"))
}

#[tauri::command]
pub fn install_update(
    app: AppHandle,
    state: State<'_, AppState>,
    us: State<'_, UpdateState>,
) -> Result<(), String> {
    state.activity.ensure_idle()?;
    let Some((update, bytes)) = us.ready.lock().unwrap().take() else {
        return Err("No downloaded update is ready to install.".into());
    };
    if let Err(e) = update.install(&bytes) {
        // Keep the bytes so the user can retry; the installed app is untouched.
        let msg = friendly(&e.to_string());
        *us.ready.lock().unwrap() = Some((update, bytes));
        return Err(msg);
    }
    app.restart();
}

#[cfg(test)]
mod tests {
    use super::friendly;

    #[test]
    fn errors_are_explained() {
        assert!(friendly("error sending request: dns error").contains("offline"));
        assert!(friendly("minisign error: signature mismatch").contains("signature verification"));
        assert!(friendly("status 404 Not Found").contains("No published release"));
    }
}
