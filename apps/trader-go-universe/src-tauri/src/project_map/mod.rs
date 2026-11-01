//! Project Map: a JSON Canvas of how project files connect, kept current by a file watcher.
//! Indexing is deterministic and local. No network, no LLM.

pub mod canvas;
pub mod engine;
pub mod index;
pub mod links;
pub mod obsidian;

use engine::{Engine, MapError};
use notify_debouncer_full::notify::{
    event::{ModifyKind, RenameMode},
    EventKind, RecursiveMode,
};
use notify_debouncer_full::{new_debouncer, DebounceEventResult};
use serde::Serialize;
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, RecvTimeoutError, Sender};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tauri::{AppHandle, Emitter, Manager, State};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_opener::OpenerExt;

pub const STATUS_EVENT: &str = "map-status";
pub const CHANGED_EVENT: &str = "map-changed";
const DEBOUNCE: Duration = Duration::from_millis(700);
const RETRY: Duration = Duration::from_secs(5);
const SETTLE: Duration = Duration::from_secs(2);

#[derive(Debug, Clone, Serialize, Default)]
pub struct Status {
    /// unconfigured | indexing | idle | error
    pub state: &'static str,
    pub root: Option<String>,
    pub message: Option<String>,
    pub files: usize,
    pub edges: usize,
    pub unconnected: usize,
    pub last_run: u128,
    /// Diagnostics: connections per kind and explicit links that point at nothing.
    pub by_kind: std::collections::BTreeMap<String, usize>,
    pub broken: Vec<engine::BrokenLink>,
}

#[derive(Debug, Clone, Serialize)]
struct Changed {
    /// true when the map file was changed by something other than Trader_go.
    external: bool,
}

enum Msg {
    SetRoot(Option<PathBuf>),
    Refresh,
    Fs(DebounceEventResult),
}

pub struct MapService {
    tx: Mutex<Sender<Msg>>,
    engine: Arc<Mutex<Option<Engine>>>,
    status: Arc<Mutex<Status>>,
}

fn now_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0)
}

impl MapService {
    pub fn start(app: AppHandle, meta_dir: PathBuf, root: Option<PathBuf>) -> Self {
        let (tx, rx) = channel::<Msg>();
        let engine: Arc<Mutex<Option<Engine>>> = Arc::default();
        let status = Arc::new(Mutex::new(Status {
            state: "unconfigured",
            ..Default::default()
        }));
        let (eng, st, fs_tx) = (engine.clone(), status.clone(), tx.clone());

        std::thread::spawn(move || {
            let mut watcher = None;
            let mut retry_at: Option<Instant> = None;
            let mut settle_at: Option<Instant> = None;

            let set_status = |s: Status| {
                *st.lock().unwrap() = s.clone();
                let _ = app.emit(STATUS_EVENT, s);
            };
            let run = |hints: &[(String, String)]| -> bool {
                let mut guard = eng.lock().unwrap();
                let Some(e) = guard.as_mut() else {
                    return false;
                };
                let root = Some(e.root().display().to_string());
                {
                    let mut s = st.lock().unwrap().clone();
                    s.state = "indexing";
                    s.root = root.clone();
                    set_status(s);
                }
                match e.reconcile(hints) {
                    Ok(sum) => {
                        set_status(Status {
                            state: "idle",
                            root,
                            message: None,
                            files: sum.files,
                            edges: sum.edges,
                            unconnected: sum.unconnected,
                            last_run: now_ms(),
                            by_kind: sum.by_kind,
                            broken: sum.broken,
                        });
                        if sum.written {
                            let _ = app.emit(CHANGED_EVENT, Changed { external: false });
                        }
                        sum.settling
                    }
                    Err(err) => {
                        let mut s = st.lock().unwrap().clone();
                        s.state = "error";
                        s.message = Some(err.to_string());
                        set_status(s);
                        false
                    }
                }
            };

            let tx_for_watch = fs_tx;
            let start_watch = |root: &Path| {
                let tx = tx_for_watch.clone();
                let mut d = new_debouncer(DEBOUNCE, None, move |res| {
                    let _ = tx.send(Msg::Fs(res));
                })
                .ok()?;
                d.watch(root, RecursiveMode::Recursive).ok()?;
                Some(d)
            };

            let mut pending_root = Some(root);
            loop {
                if let Some(r) = pending_root.take() {
                    watcher = None;
                    settle_at = None;
                    *eng.lock().unwrap() = r.as_ref().map(|r| Engine::open(r, &meta_dir));
                    match r {
                        None => set_status(Status {
                            state: "unconfigured",
                            ..Default::default()
                        }),
                        Some(r) => {
                            if run(&[]) {
                                settle_at = Some(Instant::now() + SETTLE);
                            }
                            watcher = start_watch(&r);
                            retry_at = watcher.is_none().then(|| Instant::now() + RETRY);
                        }
                    }
                }

                let wait = [retry_at, settle_at]
                    .into_iter()
                    .flatten()
                    .min()
                    .map(|t| t.saturating_duration_since(Instant::now()))
                    .unwrap_or(Duration::from_secs(3600));
                match rx.recv_timeout(wait) {
                    Ok(Msg::SetRoot(r)) => pending_root = Some(r),
                    Ok(Msg::Refresh) => {
                        settle_at = run(&[]).then(|| Instant::now() + SETTLE);
                    }
                    Ok(Msg::Fs(Err(_))) => {
                        // Folder gone or watcher broke (unplugged drive, network share): re-arm.
                        watcher = None;
                        retry_at = Some(Instant::now());
                    }
                    Ok(Msg::Fs(Ok(events))) => {
                        let Some(root) =
                            eng.lock().unwrap().as_ref().map(|e| e.root().to_path_buf())
                        else {
                            continue;
                        };
                        let canvas = root.join(index::MAP_FILE);
                        let rel = |p: &Path| {
                            p.strip_prefix(&root)
                                .ok()
                                .map(|r| r.to_string_lossy().replace('\\', "/"))
                        };
                        let mut relevant = false;
                        let mut canvas_touched = false;
                        let mut hints = Vec::new();
                        for ev in &events {
                            if matches!(ev.kind, EventKind::Access(_)) {
                                continue;
                            }
                            if let EventKind::Modify(ModifyKind::Name(RenameMode::Both)) = ev.kind {
                                if let (Some(a), Some(b)) = (
                                    ev.paths.first().and_then(|p| rel(p)),
                                    ev.paths.get(1).and_then(|p| rel(p)),
                                ) {
                                    hints.push((a, b));
                                }
                            }
                            for p in &ev.paths {
                                if *p == canvas {
                                    canvas_touched = true;
                                } else if let Some(r) = rel(p) {
                                    if !index::is_excluded_rel(&r) {
                                        relevant = true;
                                    }
                                }
                            }
                        }
                        if !root.is_dir() {
                            watcher = None;
                            retry_at = Some(Instant::now() + RETRY);
                            let mut s = st.lock().unwrap().clone();
                            s.state = "error";
                            s.message = Some(
                                "Projektmappen är inte tillgänglig just nu. Försöker igen.".into(),
                            );
                            set_status(s);
                            continue;
                        }
                        // Our own writes are recognised by hash, so they never trigger a pass.
                        if canvas_touched
                            && !eng
                                .lock()
                                .unwrap()
                                .as_ref()
                                .is_some_and(|e| e.is_own_write())
                        {
                            let _ = app.emit(CHANGED_EVENT, Changed { external: true });
                            relevant = true;
                        }
                        if relevant {
                            settle_at = run(&hints).then(|| Instant::now() + SETTLE);
                        }
                    }
                    Err(RecvTimeoutError::Timeout) => {
                        let now = Instant::now();
                        if settle_at.is_some_and(|t| t <= now) {
                            settle_at = run(&[]).then(|| Instant::now() + SETTLE);
                        }
                        if retry_at.is_some_and(|t| t <= now) {
                            retry_at = None;
                            let root = eng.lock().unwrap().as_ref().map(|e| e.root().to_path_buf());
                            if let Some(root) = root {
                                if root.is_dir() {
                                    run(&[]);
                                    watcher = start_watch(&root);
                                }
                                if watcher.is_none() {
                                    retry_at = Some(Instant::now() + RETRY);
                                }
                            }
                        }
                    }
                    Err(RecvTimeoutError::Disconnected) => break,
                }
            }
        });

        MapService {
            tx: Mutex::new(tx),
            engine,
            status,
        }
    }

    fn send(&self, m: Msg) {
        let _ = self.tx.lock().unwrap().send(m);
    }

    fn with_engine<T>(
        &self,
        f: impl FnOnce(&mut Engine) -> Result<T, MapError>,
    ) -> Result<T, String> {
        let mut g = self.engine.lock().unwrap();
        let e = g.as_mut().ok_or("Ingen projektmapp är vald.")?;
        f(e).map_err(|e| match e {
            MapError::Conflict => format!("CONFLICT: {e}"),
            other => other.to_string(),
        })
    }
}

#[derive(Serialize)]
pub struct MapInfo {
    status: Status,
    canvas_path: Option<String>,
    obsidian_installed: bool,
    obsidian_vault: Option<String>,
}

#[derive(Serialize)]
pub struct Loaded {
    doc: Value,
    hash: String,
}

impl MapService {
    /// Points the map at a folder found after startup (no setting is saved).
    pub fn use_root(&self, path: PathBuf) {
        self.send(Msg::SetRoot(Some(path)));
    }
}

fn set_root(app: &AppHandle, svc: &MapService, path: PathBuf) -> Result<(), String> {
    if !path.is_absolute() || !path.is_dir() {
        return Err("Välj en befintlig mapp.".into());
    }
    crate::universe::save_custom_root(app, Some(&path))?;
    svc.send(Msg::SetRoot(Some(path)));
    Ok(())
}


#[tauri::command]
pub fn map_info(svc: State<'_, MapService>) -> MapInfo {
    let status = svc.status.lock().unwrap().clone();
    let canvas = svc.engine.lock().unwrap().as_ref().map(|e| e.canvas_path());
    let vault = canvas.as_deref().and_then(obsidian::vault_for);
    MapInfo {
        status,
        canvas_path: canvas.map(|p| p.display().to_string()),
        obsidian_installed: obsidian::installed(),
        obsidian_vault: vault.map(|v| v.display().to_string()),
    }
}

#[tauri::command]
pub async fn map_choose_root(app: AppHandle) -> Result<bool, String> {
    let Some(picked) = app
        .dialog()
        .file()
        .set_title("Välj projektmapp")
        .blocking_pick_folder()
    else {
        return Ok(false);
    };
    let path = picked.into_path().map_err(|e| e.to_string())?;
    set_root(&app, &app.state::<MapService>(), path)?;
    Ok(true)
}

#[tauri::command]
pub fn map_refresh(svc: State<'_, MapService>) {
    svc.send(Msg::Refresh);
}

#[tauri::command]
pub fn map_load(svc: State<'_, MapService>) -> Result<Loaded, String> {
    svc.with_engine(|e| e.load().map(|(doc, hash)| Loaded { doc, hash }))
}

#[tauri::command]
pub fn map_save(
    doc: Value,
    base_hash: String,
    svc: State<'_, MapService>,
) -> Result<String, String> {
    svc.with_engine(|e| e.save(&doc, &base_hash))
}

#[tauri::command]
pub fn map_save_copy(doc: Value, svc: State<'_, MapService>) -> Result<String, String> {
    svc.with_engine(|e| e.save_copy(&doc))
}

#[tauri::command]
pub async fn map_export(app: AppHandle, doc: Value) -> Result<Option<String>, String> {
    engine::validate_canvas(&doc).map_err(|e| e.to_string())?;
    let Some(dest) = app
        .dialog()
        .file()
        .add_filter("JSON Canvas", &["canvas"])
        .set_file_name("Project Map export.canvas")
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let path = dest.into_path().map_err(|e| e.to_string())?;
    // Universe never writes into the project it watches.
    let root = app.state::<MapService>().engine.lock().unwrap().as_ref().map(|e| e.root().to_path_buf());
    let parent = path.parent().and_then(|p| p.canonicalize().ok());
    if let (Some(root), Some(parent)) = (root.and_then(|r| r.canonicalize().ok()), parent) {
        if parent.starts_with(&root) {
            return Err("Spara exporten utanför projektmappen. Universe skriver aldrig i projektet.".into());
        }
    }
    engine::atomic_write(&path, &engine::to_bytes(&doc)).map_err(|e| e.to_string())?;
    Ok(Some(path.display().to_string()))
}

#[tauri::command]
pub fn map_preview(path: String, svc: State<'_, MapService>) -> Result<engine::Preview, String> {
    svc.with_engine(|e| e.preview(&path))
}

/// Shows the file in Finder/Explorer. Never opens or runs it.
#[tauri::command]
pub fn map_reveal(app: AppHandle, path: String, svc: State<'_, MapService>) -> Result<(), String> {
    let full = svc.with_engine(|e| e.resolve_file(&path))?;
    app.opener()
        .reveal_item_in_dir(full)
        .map_err(|e| e.to_string())
}

/// Opens the map (or a file on it) in Obsidian through its URL scheme.
#[tauri::command]
pub fn map_open_obsidian(
    app: AppHandle,
    path: Option<String>,
    svc: State<'_, MapService>,
) -> Result<(), String> {
    let target = match path {
        Some(p) => svc.with_engine(|e| e.resolve_file(&p))?,
        None => svc.with_engine(|e| Ok(e.canvas_path()))?,
    };
    if !obsidian::installed() {
        return Err("Obsidian är inte installerat.".into());
    }
    if obsidian::vault_for(&target).is_none() {
        return Err(
            "Mappen är inte ett Obsidian-valv. Öppna projektmappen som valv i Obsidian först."
                .into(),
        );
    }
    app.opener()
        .open_url(obsidian::open_url(&target), None::<&str>)
        .map_err(|e| e.to_string())
}
