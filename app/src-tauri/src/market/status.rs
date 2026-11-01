//! Maskinläsbar status för insamlingen. Visas i appens Status-vy och skrivs som `market/status.json` i
//! appens datamapp, så att andra program (till exempel Universe) kan läsa den utan att röra databasen.

use serde::Serialize;
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum State {
    Starting,
    Syncing,
    Connected,
    Reconnecting,
    /// Staplar saknas och kunde inte hämtas än.
    Gap,
    /// Inga meddelanden inom förväntad tid, eller senaste stängda stapel är för gammal.
    Stale,
    Stopped,
    Error,
}

#[derive(Debug, Clone, Serialize)]
pub struct Status {
    /// Ändras om fälten ändras på ett sätt som bryter läsare.
    pub schema: u32,
    pub state: State,
    /// Sant bara när historiken är komplett, strömmen är ansluten och datan är färsk.
    pub ready: bool,
    pub provider: String,
    pub market: String,
    pub symbol: String,
    pub interval: String,
    pub message: Option<String>,
    /// Datorns tid när senaste meddelande togs emot (ms UTC).
    pub last_received_at: Option<i64>,
    /// Serverns tid för senaste händelse (ms UTC).
    pub last_event_time: Option<i64>,
    pub last_closed_open_time: Option<i64>,
    pub live_open_time: Option<i64>,
    pub closed_bars: i64,
    pub gaps: Vec<(i64, i64)>,
    pub confirmed_gaps: usize,
    pub corrections: i64,
    pub rejected: u64,
    pub reconnects: u64,
    pub updated_at: i64,
    pub database: String,
}

impl Status {
    pub fn new(provider: &str, market: &str, symbol: &str, interval: &str, database: &str) -> Self {
        Status {
            schema: 1,
            state: State::Starting,
            ready: false,
            provider: provider.into(),
            market: market.into(),
            symbol: symbol.into(),
            interval: interval.into(),
            message: None,
            last_received_at: None,
            last_event_time: None,
            last_closed_open_time: None,
            live_open_time: None,
            closed_bars: 0,
            gaps: vec![],
            confirmed_gaps: 0,
            corrections: 0,
            rejected: 0,
            reconnects: 0,
            updated_at: 0,
            database: database.into(),
        }
    }

    pub fn set(&mut self, state: State, message: Option<String>) {
        self.state = state;
        self.message = message;
        self.ready = state == State::Connected;
    }
}

/// Är den senaste stängda stapeln för gammal? Den stapel som stängde senast ska finnas inom en tidsram
/// plus marginal; annars saknas data även om strömmen pratar.
pub fn closed_is_behind(last_closed_open: Option<i64>, step: i64, now: i64, grace_ms: i64) -> bool {
    match last_closed_open {
        None => true,
        Some(t) => now - (t + step) > step + grace_ms,
    }
}

/// Har strömmen tystnat? Bedöms mot strömmens takt (Binance: var 2:a sekund, ping var 20:e), inte mot
/// tidsramen.
pub fn stream_is_silent(
    last_received_mono_ms: u128,
    now_mono_ms: u128,
    stale_after_ms: u128,
) -> bool {
    now_mono_ms.saturating_sub(last_received_mono_ms) > stale_after_ms
}

/// Skriver status atomiskt (temporär fil + byt namn), så att en läsare aldrig ser en halv fil.
pub fn write_atomic(path: &Path, status: &Status) -> std::io::Result<()> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;
    }
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, serde_json::to_vec_pretty(status).unwrap_or_default())?;
    for attempt in 0..5 {
        match std::fs::rename(&tmp, path) {
            Ok(()) => return Ok(()),
            // Windows: en läsare kan ha filen öppen en kort stund.
            Err(_) if attempt < 4 => std::thread::sleep(std::time::Duration::from_millis(50)),
            Err(e) => return Err(e),
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    const STEP: i64 = 14_400_000;

    #[test]
    fn closed_data_is_behind_only_after_a_missed_close() {
        let t = 1_793_520_000_000;
        assert!(
            !closed_is_behind(Some(t), STEP, t + STEP + 1, 60_000),
            "just after close, the next bar is still open"
        );
        assert!(!closed_is_behind(Some(t), STEP, t + 2 * STEP, 60_000));
        assert!(
            closed_is_behind(Some(t), STEP, t + 2 * STEP + 120_000, 60_000),
            "a whole bar closed and never arrived"
        );
        assert!(closed_is_behind(None, STEP, t, 60_000));
    }

    #[test]
    fn silence_is_judged_by_stream_rate() {
        assert!(!stream_is_silent(0, 25_000, 30_000));
        assert!(stream_is_silent(0, 31_000, 30_000));
    }

    #[test]
    fn ready_only_when_connected() {
        let mut s = Status::new("binance", "spot", "BTCUSDT", "4h", "x");
        for st in [
            State::Starting,
            State::Syncing,
            State::Gap,
            State::Stale,
            State::Reconnecting,
            State::Error,
            State::Stopped,
        ] {
            s.set(st, None);
            assert!(!s.ready, "{st:?}");
        }
        s.set(State::Connected, None);
        assert!(s.ready);
        assert_eq!(serde_json::to_value(&s).unwrap()["state"], "connected");
    }

    #[test]
    fn status_file_is_replaced_whole() {
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join("market").join("status.json");
        let mut s = Status::new("binance", "spot", "BTCUSDT", "4h", "x");
        write_atomic(&p, &s).unwrap();
        s.set(State::Connected, None);
        write_atomic(&p, &s).unwrap();
        let v: serde_json::Value = serde_json::from_slice(&std::fs::read(&p).unwrap()).unwrap();
        assert_eq!(v["state"], "connected");
        assert!(!p.with_extension("json.tmp").exists());
    }
}
