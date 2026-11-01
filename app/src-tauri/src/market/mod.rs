//! Insamling av publik marknadsdata (punkt 2 i planen). Bara läsning av publik data: inga nycklar,
//! inga konton, inga order. Datan sparas lokalt i appens datamapp på varje dator; det finns ingen
//! gemensam server, så två datorer har var sin insamling och ingen gemensam papperssession.
//!
//! Filer i `<appdata>/market/`:
//! - `market-data.sqlite`  stängda staplar, pågående stapel, rättelser, luckor, hämtningslogg (schema.sql)
//! - `status.json`         maskinläsbar status (status.rs), för Status-vyn och för Universe
//! - `config.json`         valfri: symbol, tidsram, uppvärmning (model::Config)
//! - `collector.lock`      hindrar två insamlare från att skriva samtidigt

pub mod model;
pub mod runner;
pub mod source;
pub mod status;
pub mod store;
pub mod sync;

use model::Config;
use status::{State, Status};
use std::fs::File;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::JoinHandle;
use std::time::Duration;

pub const STATUS_EVENT: &str = "market-status";

pub struct Collector {
    pub status: Arc<Mutex<Status>>,
    stop: Arc<AtomicBool>,
    handle: Mutex<Option<JoinHandle<()>>>,
    _lock: Option<File>,
}

/// Läser `config.json` om den finns. Ett fel i filen stoppar insamlingen med ett tydligt fel; ingen tyst
/// återgång till standard eller till simulerad data.
pub fn load_config(dir: &Path) -> Result<Config, String> {
    let path = dir.join("config.json");
    let cfg = match std::fs::read(&path) {
        Ok(bytes) => serde_json::from_slice::<Config>(&bytes).map_err(|e| format!("{}: {e}", path.display()))?,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Config::default(),
        Err(e) => return Err(format!("{}: {e}", path.display())),
    };
    cfg.validate()?;
    Ok(cfg)
}

impl Collector {
    /// Startar insamlingen i en egen tråd. `publish` anropas vid varje statusändring.
    pub fn start(dir: PathBuf, publish: Box<dyn Fn(&Status) + Send>) -> Collector {
        let db = dir.join("market-data.sqlite");
        let status_file = dir.join("status.json");
        let stop = Arc::new(AtomicBool::new(false));
        let fail = |status: Status, msg: String, publish: &dyn Fn(&Status)| {
            let mut s = status;
            s.set(State::Error, Some(msg));
            s.updated_at = runner::now_ms();
            let _ = status::write_atomic(&status_file, &s);
            publish(&s);
            Collector { status: Arc::new(Mutex::new(s)), stop: stop.clone(), handle: Mutex::new(None), _lock: None }
        };
        let blank = |c: &Config| Status::new(&c.provider, &c.market, &c.symbol, &c.interval, &db.display().to_string());

        if let Err(e) = std::fs::create_dir_all(&dir) {
            return fail(blank(&Config::default()), format!("kan inte skapa {}: {e}", dir.display()), publish.as_ref());
        }
        let cfg = match load_config(&dir) {
            Ok(c) => c,
            Err(e) => return fail(blank(&Config::default()), format!("ogiltig inställning: {e}"), publish.as_ref()),
        };
        // En insamlare per datamapp. Låset släpps när processen avslutas, också vid krasch.
        let lock = match File::options().create(true).truncate(false).write(true).open(dir.join("collector.lock")) {
            Ok(f) => f,
            Err(e) => return fail(blank(&cfg), format!("kan inte öppna låsfilen: {e}"), publish.as_ref()),
        };
        if lock.try_lock().is_err() {
            return fail(blank(&cfg), "en annan TraderGO samlar redan in data i den här datamappen".into(), publish.as_ref());
        }
        let store = match store::Store::open(&db) {
            Ok(s) => s,
            Err(e) => return fail(blank(&cfg), format!("kan inte öppna databasen: {e}"), publish.as_ref()),
        };
        let http = match source::UreqHttp::new() {
            Ok(h) => h,
            Err(e) => return fail(blank(&cfg), format!("TLS kunde inte startas: {e}"), publish.as_ref()),
        };
        let status = Arc::new(Mutex::new(blank(&cfg)));
        let status_file2 = status_file.clone();
        let publish_all: Box<dyn Fn(&Status) + Send> = Box::new(move |s: &Status| {
            let _ = status::write_atomic(&status_file2, s);
            publish(s);
        });
        let runner = runner::Runner::new(&cfg, Box::new(source::Binance::new(http)), store, status.clone(), publish_all, stop.clone(), runner::Timing::default());
        let handle = std::thread::Builder::new().name("market-collector".into()).spawn(move || runner.run()).ok();
        Collector { status, stop, handle: Mutex::new(handle), _lock: Some(lock) }
    }

    pub fn snapshot(&self) -> Status {
        self.status.lock().unwrap().clone()
    }

    /// Stoppar kontrollerat: stänger anslutningen och väntar högst `timeout` på att tråden avslutas.
    pub fn stop(&self, timeout: Duration) {
        self.stop.store(true, Ordering::SeqCst);
        if let Some(h) = self.handle.lock().unwrap().take() {
            let end = std::time::Instant::now() + timeout;
            while !h.is_finished() && std::time::Instant::now() < end {
                std::thread::sleep(Duration::from_millis(20));
            }
            if h.is_finished() {
                let _ = h.join();
            }
        }
    }
}

#[tauri::command]
pub fn market_status(state: tauri::State<'_, Collector>) -> Status {
    state.snapshot()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_broken_config_stops_with_an_error_and_no_fallback() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("config.json"), r#"{"provider":"binance","market":"spot","symbol":"DOGEUSDT","interval":"4h"}"#).unwrap();
        let c = Collector::start(dir.path().to_path_buf(), Box::new(|_| {}));
        let s = c.snapshot();
        assert_eq!(s.state, State::Error);
        assert!(s.message.unwrap().contains("DOGEUSDT"));
        assert!(!s.ready);
        let file: serde_json::Value = serde_json::from_slice(&std::fs::read(dir.path().join("status.json")).unwrap()).unwrap();
        assert_eq!(file["state"], "error");
    }

    /// Riktigt nätverkstest mot Binance publika marknadsdata. Körs bara med
    /// `cargo test real_network -- --ignored`, aldrig i CI eller de vanliga testerna.
    #[test]
    #[ignore]
    fn real_network_collects_closed_history_and_a_live_bar() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("config.json"), r#"{"provider":"binance","market":"spot","symbol":"BTCUSDT","interval":"4h","warmup_bars":50}"#).unwrap();
        let c = Collector::start(dir.path().to_path_buf(), Box::new(|_| {}));
        let end = std::time::Instant::now() + Duration::from_secs(30);
        while std::time::Instant::now() < end {
            let s = c.snapshot();
            if s.ready && s.live_open_time.is_some() && s.last_received_at.is_some() {
                break;
            }
            std::thread::sleep(Duration::from_millis(200));
        }
        let s = c.snapshot();
        c.stop(Duration::from_secs(5));
        println!("{}", serde_json::to_string_pretty(&s).unwrap());
        assert!(s.ready, "inte redo: {:?} {:?}", s.state, s.message);
        assert_eq!(s.closed_bars, 50);
        assert!(s.gaps.is_empty());
        assert!(s.last_received_at.is_some() && s.last_event_time.is_some(), "inget meddelande från strömmen");
        let live = s.live_open_time.unwrap();
        assert_eq!(s.last_closed_open_time, Some(live - 14_400_000), "pågående stapel direkt efter senaste stängda");
        assert_eq!(c.snapshot().state, State::Stopped);
    }

    #[test]
    fn a_second_collector_on_the_same_folder_is_refused() {
        let dir = tempfile::tempdir().unwrap();
        // Ingen nätverksåtkomst behövs: den första håller låset även om den inte kommer någonstans.
        let first = Collector::start(dir.path().to_path_buf(), Box::new(|_| {}));
        let second = Collector::start(dir.path().to_path_buf(), Box::new(|_| {}));
        assert_eq!(second.snapshot().state, State::Error);
        assert!(second.snapshot().message.unwrap().contains("en annan"));
        first.stop(Duration::from_secs(15));
    }
}
