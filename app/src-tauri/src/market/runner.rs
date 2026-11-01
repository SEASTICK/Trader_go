//! Insamlingsloopen: ansluter strömmen, kommer ikapp via REST, läser händelser och återansluter med
//! exponentiell backoff och slumpad väntan. Körs i en egen tråd och stoppas med `stop`.
//!
//! - Binance pingar var 20:e sekund och kopplar ner om ingen pong kommer inom en minut; tungstenite svarar
//!   med pong automatiskt, och vi skickar den direkt med flush.
//! - En anslutning lever högst 24 timmar och `serverShutdown` varnar för planerade avbrott; båda ger en
//!   kontrollerad återanslutning med REST-ikappkörning.
//! - Vila och nätverksavbrott märks på att strömmen tystnar eller att väggklockan hoppar mot den monotona.

use super::model::Config;
use super::source::{Source, SourceError, StreamMsg};
use super::status::{closed_is_behind, stream_is_silent, State, Status};
use super::store::Store;
use super::sync::{Applied, Sync, SyncError};
use std::net::TcpStream;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tungstenite::stream::MaybeTlsStream;
use tungstenite::{Message, WebSocket};

pub fn now_ms() -> i64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_millis() as i64).unwrap_or(0)
}

#[derive(Debug, Clone)]
pub struct Timing {
    pub backoff_base: Duration,
    pub backoff_cap: Duration,
    pub read_tick: Duration,
    /// Återanslut i god tid före Binances 24-timmarsgräns.
    pub max_connection_age: Duration,
    /// En anslutning som hållit så länge nollställer backoffen.
    pub healthy_after: Duration,
    /// Marginal innan en saknad stängd stapel räknas som gammal data.
    pub close_grace: Duration,
}

impl Default for Timing {
    fn default() -> Self {
        Timing {
            backoff_base: Duration::from_secs(1),
            backoff_cap: Duration::from_secs(60),
            read_tick: Duration::from_secs(1),
            max_connection_age: Duration::from_secs(23 * 3600 + 30 * 60),
            healthy_after: Duration::from_secs(60),
            close_grace: Duration::from_secs(120),
        }
    }
}

/// Exponentiell backoff med slumpad väntan ("equal jitter"): halva fördröjningen fast, halva slumpad.
pub struct Backoff {
    pub attempt: u32,
    base: Duration,
    cap: Duration,
}

impl Backoff {
    pub fn new(base: Duration, cap: Duration) -> Self {
        Backoff { attempt: 0, base, cap }
    }
    pub fn next(&mut self) -> Duration {
        let exp = self.base.saturating_mul(1u32 << self.attempt.min(16)).min(self.cap);
        self.attempt += 1;
        let half = exp / 2;
        half + half.mul_f64(fastrand::f64())
    }
    pub fn reset(&mut self) {
        self.attempt = 0;
    }
}

/// Väggklockan gick mycket längre än den monotona klockan: datorn har sovit.
pub fn woke_from_sleep(mono: Duration, wall: Duration) -> bool {
    wall.saturating_sub(mono) > Duration::from_secs(10)
}

/// En stapel till diagrammen. `resync`: staplar kom via REST (ikappkörning eller lucka); läs om slutet.
#[derive(Debug, Clone, serde::Serialize, PartialEq)]
pub struct BarEvent {
    pub provider: String,
    pub market: String,
    pub symbol: String,
    pub interval: String,
    /// live | closed | resync
    pub kind: &'static str,
    pub bar: Option<super::model::Bar>,
}

enum Exit {
    Stop,
    Reconnect(String),
}

pub struct Runner {
    src: Box<dyn Source>,
    store: Store,
    sync: Sync,
    stale_after: Duration,
    timing: Timing,
    pub status: Arc<Mutex<Status>>,
    publish: Box<dyn Fn(&Status) + Send>,
    on_bar: Box<dyn Fn(&BarEvent) + Send>,
    stop: Arc<AtomicBool>,
    last_publish: Option<Instant>,
}

impl Runner {
    pub fn new(cfg: &Config, src: Box<dyn Source>, store: Store, status: Arc<Mutex<Status>>, publish: Box<dyn Fn(&Status) + Send>, stop: Arc<AtomicBool>, timing: Timing) -> Self {
        assert_eq!(cfg.provider, src.name(), "konfigurationen och källan måste vara samma leverantör");
        // Aldrig tätare än tio uteblivna meddelanden i strömmens egen takt.
        let stale_after = Duration::from_secs(cfg.stale_after_secs).max(src.stream_period() * 10);
        Runner { src, store, sync: Sync::new(cfg), stale_after, timing, status, publish, on_bar: Box::new(|_| {}), stop, last_publish: None }
    }

    /// Diagrammen lyssnar här i stället för att öppna egna anslutningar.
    pub fn with_bar_listener(mut self, f: Box<dyn Fn(&BarEvent) + Send>) -> Self {
        self.on_bar = f;
        self
    }

    fn emit_bar(&self, kind: &'static str, bar: Option<super::model::Bar>) {
        let k = &self.sync.key;
        (self.on_bar)(&BarEvent { provider: k.provider.clone(), market: k.market.clone(), symbol: k.symbol.clone(), interval: k.interval.clone(), kind, bar });
    }

    fn stopping(&self) -> bool {
        self.stop.load(Ordering::SeqCst)
    }

    /// Räknar om siffrorna från databasen och publicerar. `force` publicerar direkt, annars högst en gång per sekund.
    fn update(&mut self, state: Option<(State, Option<String>)>, force: bool) {
        let k = &self.sync.key;
        let (_, last, n) = self.store.range(k).unwrap_or((None, None, 0));
        let gaps = self.store.missing_ranges(k, self.sync.step).unwrap_or_default();
        let confirmed = self.store.confirmed_gaps(k).map(|g| g.len()).unwrap_or(0);
        let corrections = self.store.correction_count(k).unwrap_or(0);
        let live = self.store.live(k).ok().flatten().map(|b| b.open_time);
        let snapshot = {
            let mut s = self.status.lock().unwrap();
            if let Some((st, msg)) = state {
                s.set(st, msg);
            }
            s.last_closed_open_time = last;
            s.closed_bars = n;
            s.gaps = gaps;
            s.confirmed_gaps = confirmed;
            s.corrections = corrections;
            s.live_open_time = live;
            s.updated_at = now_ms();
            s.clone()
        };
        if force || self.last_publish.is_none_or(|t| t.elapsed() >= Duration::from_secs(1)) {
            (self.publish)(&snapshot);
            self.last_publish = Some(Instant::now());
        }
    }

    fn sleep(&self, d: Duration) {
        let end = Instant::now() + d;
        while Instant::now() < end && !self.stopping() {
            std::thread::sleep(Duration::from_millis(50).min(end.saturating_duration_since(Instant::now())));
        }
    }

    /// REST-ikappkörning och luckfyllnad. Returnerar luckor som finns kvar.
    fn catch_up(&mut self) -> Result<Vec<(i64, i64)>, SyncError> {
        let rep = self.sync.backfill(self.src.as_ref(), &mut self.store, now_ms())?;
        self.status.lock().unwrap().rejected += rep.rejected as u64;
        let gaps = self.sync.fill_gaps(self.src.as_ref(), &mut self.store, now_ms())?;
        self.emit_bar("resync", None);
        Ok(gaps)
    }

    pub fn run(mut self) {
        self.update(Some((State::Starting, None)), true);
        let mut backoff = Backoff::new(self.timing.backoff_base, self.timing.backoff_cap);
        let mut first = true;
        while !self.stopping() {
            let state = if first { State::Syncing } else { State::Reconnecting };
            self.update(Some((state, None)), true);
            first = false;

            // 1. Strömmen först, så att händelser under REST-hämtningen väntar i socketbufferten.
            let url = self.src.stream_url(&self.sync.key.symbol, &self.sync.key.interval);
            let mut ws = match connect(&url, self.timing.read_tick) {
                Ok(ws) => ws,
                Err(e) => {
                    let wait = backoff.next();
                    self.update(Some((State::Reconnecting, Some(format!("kunde inte ansluta strömmen: {e}; nytt försök om {} s", wait.as_secs())))), true);
                    self.sleep(wait);
                    continue;
                }
            };
            // 2. Historiken via REST, sedan luckor.
            self.update(Some((State::Syncing, None)), true);
            match self.catch_up() {
                Ok(gaps) if gaps.is_empty() => self.update(Some((State::Connected, None)), true),
                Ok(gaps) => self.update(Some((State::Gap, Some(format!("{} luckor kunde inte fyllas än", gaps.len())))), true),
                Err(e) => {
                    let wait = match &e {
                        SyncError::Source(SourceError::RateLimited { retry_after_secs, .. }) => Duration::from_secs(*retry_after_secs),
                        _ => backoff.next(),
                    };
                    let state = if matches!(e, SyncError::Store(_)) { State::Error } else { State::Reconnecting };
                    self.update(Some((state, Some(format!("{e}; nytt försök om {} s", wait.as_secs())))), true);
                    let _ = ws.close(None);
                    self.sleep(wait);
                    continue;
                }
            }
            // 3. Läs strömmen.
            let started = Instant::now();
            let exit = self.read_loop(&mut ws, started);
            if started.elapsed() >= self.timing.healthy_after {
                backoff.reset();
            }
            let _ = ws.close(None);
            let _ = ws.flush();
            match exit {
                Exit::Stop => break,
                Exit::Reconnect(why) => {
                    self.status.lock().unwrap().reconnects += 1;
                    let wait = backoff.next();
                    self.update(Some((State::Reconnecting, Some(format!("{why}; ansluter igen om {} s", wait.as_secs())))), true);
                    self.sleep(wait);
                }
            }
        }
        self.update(Some((State::Stopped, None)), true);
    }

    fn read_loop(&mut self, ws: &mut WebSocket<MaybeTlsStream<TcpStream>>, started: Instant) -> Exit {
        let mut last_msg = Instant::now();
        let mut tick_mono = Instant::now();
        let mut tick_wall = SystemTime::now();
        loop {
            if self.stopping() {
                return Exit::Stop;
            }
            match ws.read() {
                Ok(Message::Text(text)) => {
                    last_msg = Instant::now();
                    let received = now_ms();
                    match self.src.parse_stream(&*text) {
                        Ok(StreamMsg::Kline { bar, closed, event_time, symbol, interval }) => {
                            if symbol != self.sync.key.symbol || interval != self.sync.key.interval {
                                continue;
                            }
                            {
                                let mut s = self.status.lock().unwrap();
                                s.last_received_at = Some(received);
                                s.last_event_time = Some(event_time);
                            }
                            match self.sync.apply(&mut self.store, &bar, closed, event_time, received) {
                                Ok(Applied::GapDetected { .. }) => {
                                    self.emit_bar("closed", Some(bar));
                                    match self.catch_up() {
                                        Ok(gaps) if gaps.is_empty() => self.update(Some((State::Connected, None)), true),
                                        Ok(gaps) => self.update(Some((State::Gap, Some(format!("{} luckor kunde inte fyllas än", gaps.len())))), true),
                                        Err(e) => return Exit::Reconnect(format!("kunde inte fylla luckan: {e}")),
                                    }
                                }
                                Ok(Applied::Rejected(why)) => {
                                    self.status.lock().unwrap().rejected += 1;
                                    self.update(None, false);
                                    let _ = why;
                                }
                                Ok(Applied::Closed { .. }) => {
                                    self.emit_bar("closed", Some(bar));
                                    self.update(Some((State::Connected, None)), true)
                                }
                                Ok(Applied::Live) => {
                                    self.emit_bar("live", Some(bar));
                                    let restore = self.status.lock().unwrap().state == State::Stale;
                                    self.update(restore.then_some((State::Connected, None)), false);
                                }
                                Ok(_) => {
                                    let restore = self.status.lock().unwrap().state == State::Stale;
                                    self.update(restore.then_some((State::Connected, None)), false);
                                }
                                Err(e) => {
                                    self.update(Some((State::Error, Some(e.to_string()))), true);
                                    return Exit::Reconnect(e.to_string());
                                }
                            }
                        }
                        Ok(StreamMsg::Shutdown) => return Exit::Reconnect("källan stänger anslutningen (planerat)".into()),
                        Ok(StreamMsg::Other) => {}
                        Err(why) => {
                            self.status.lock().unwrap().rejected += 1;
                            let _ = self.store.log(&self.sync.key, received, "rejected", &format!("stream: {why}"), "rejected");
                        }
                    }
                }
                Ok(Message::Ping(_)) | Ok(Message::Pong(_)) => {
                    last_msg = Instant::now();
                    let _ = ws.flush(); // skickar den pong som tungstenite köat
                }
                Ok(Message::Close(_)) => return Exit::Reconnect("källan stängde anslutningen".into()),
                Ok(_) => {}
                Err(tungstenite::Error::Io(e)) if matches!(e.kind(), std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut) => {
                    let _ = ws.flush();
                }
                Err(e) => return Exit::Reconnect(format!("anslutningen bröts: {e}")),
            }

            // Hushållning varje varv.
            let mono = tick_mono.elapsed();
            let wall = SystemTime::now().duration_since(tick_wall).unwrap_or_default();
            tick_mono = Instant::now();
            tick_wall = SystemTime::now();
            if woke_from_sleep(mono, wall) {
                return Exit::Reconnect("datorn har sovit".into());
            }
            if stream_is_silent(0, last_msg.elapsed().as_millis(), self.stale_after.as_millis()) {
                self.update(Some((State::Stale, Some(format!("inga meddelanden på {} s", self.stale_after.as_secs())))), true);
                return Exit::Reconnect("strömmen har tystnat".into());
            }
            if started.elapsed() >= self.timing.max_connection_age {
                return Exit::Reconnect("planerad återanslutning före 24-timmarsgränsen".into());
            }
            let last_closed = self.status.lock().unwrap().last_closed_open_time;
            if closed_is_behind(last_closed, self.sync.step, now_ms(), self.timing.close_grace.as_millis() as i64) {
                match self.catch_up() {
                    Ok(_) if !closed_is_behind(self.store.range(&self.sync.key).ok().and_then(|r| r.1), self.sync.step, now_ms(), self.timing.close_grace.as_millis() as i64) => {
                        self.update(Some((State::Connected, None)), true)
                    }
                    Ok(_) => self.update(Some((State::Stale, Some("senaste stängda stapel har inte kommit".into()))), true),
                    Err(e) => return Exit::Reconnect(format!("kunde inte hämta saknad stapel: {e}")),
                }
            }
        }
    }
}

/// Ansluter med tidsgräns (TCP och handskakning högst 10 s), sedan kort lästimeout för hushållningen.
fn connect(url: &str, tick: Duration) -> Result<WebSocket<MaybeTlsStream<TcpStream>>, String> {
    use std::net::ToSocketAddrs;
    let uri: tungstenite::http::Uri = url.parse().map_err(|e| format!("{e}"))?;
    let host = uri.host().ok_or("adressen saknar värd")?;
    let port = uri.port_u16().unwrap_or(if uri.scheme_str() == Some("wss") { 443 } else { 80 });
    let addrs = (host, port).to_socket_addrs().map_err(|e| format!("kan inte slå upp {host}: {e}"))?;
    let mut last = format!("ingen adress för {host}");
    let tcp = addrs
        .into_iter()
        .find_map(|a| TcpStream::connect_timeout(&a, Duration::from_secs(10)).map_err(|e| last = e.to_string()).ok())
        .ok_or(last)?;
    tcp.set_read_timeout(Some(Duration::from_secs(10))).map_err(|e| e.to_string())?;
    tcp.set_write_timeout(Some(Duration::from_secs(10))).map_err(|e| e.to_string())?;
    tcp.set_nodelay(true).ok();
    let (ws, _) = tungstenite::client_tls(url, tcp).map_err(|e| e.to_string())?;
    let tcp = match ws.get_ref() {
        MaybeTlsStream::Plain(s) => s,
        MaybeTlsStream::NativeTls(s) => s.get_ref(),
        _ => return Err("okänd anslutningstyp".into()),
    };
    tcp.set_read_timeout(Some(tick)).map_err(|e| e.to_string())?;
    Ok(ws)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::market::model::test_bar;
    use crate::market::sync::tests::{FakeSource, STEP, T0};
    use std::net::TcpListener;

    #[test]
    fn backoff_grows_has_jitter_and_caps() {
        let mut b = Backoff::new(Duration::from_secs(1), Duration::from_secs(60));
        let waits: Vec<Duration> = (0..10).map(|_| b.next()).collect();
        for (i, w) in waits.iter().enumerate() {
            let exp = Duration::from_secs(1u64 << i.min(6)).min(Duration::from_secs(60));
            assert!(*w >= exp / 2 && *w <= exp, "{i}: {w:?} not in [{:?}, {exp:?}]", exp / 2);
        }
        b.reset();
        assert!(b.next() <= Duration::from_secs(1));
    }

    #[test]
    fn sleep_is_detected_from_clock_drift() {
        assert!(!woke_from_sleep(Duration::from_secs(1), Duration::from_secs(1)));
        assert!(woke_from_sleep(Duration::from_secs(1), Duration::from_secs(600)));
    }

    /// En lokal WebSocket-server som spelar upp Binance-meddelanden, kopplar ner, och tar emot igen.
    fn kline(t: i64, closed: bool) -> String {
        let b = test_bar(t, STEP);
        format!(
            r#"{{"e":"kline","E":{},"s":"BTCUSDT","k":{{"t":{},"T":{},"s":"BTCUSDT","i":"4h","o":"{}","c":"{}","h":"{}","l":"{}","v":"{}","x":{closed}}}}}"#,
            t + 5000, b.open_time, b.close_time, b.open, b.close, b.high, b.low, b.volume
        )
    }

    struct WsSource {
        inner: FakeSource,
        url: String,
    }
    impl Source for WsSource {
        fn name(&self) -> &'static str { "binance" }
        fn server_time(&self) -> Result<i64, SourceError> { self.inner.server_time() }
        fn klines(&self, s: &str, i: &str, start: i64, l: usize, n: i64) -> Result<Vec<crate::market::source::SourceBar>, SourceError> { self.inner.klines(s, i, start, l, n) }
        fn stream_url(&self, _: &str, _: &str) -> String { self.url.clone() }
        fn parse_stream(&self, t: &str) -> Result<StreamMsg, String> { crate::market::source::parse_kline_event(t) }
        fn stream_period(&self) -> Duration { Duration::from_millis(100) }
    }

    #[test]
    fn reconnects_after_a_drop_catches_up_and_stops_cleanly() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let url = format!("ws://{}", listener.local_addr().unwrap());
        let pongs = Arc::new(Mutex::new(0));
        let pongs2 = pongs.clone();
        let (go_tx, go_rx) = std::sync::mpsc::channel::<()>();
        // Anslutning 1: en ping, stängning av stapel 3 (redan hämtad), en pågående stapel 4, sedan avbrott.
        // Anslutning 2: stapel 5 stängd (hoppar över 4) → lucka som fylls via REST.
        std::thread::spawn(move || {
            for (n, stream) in listener.incoming().enumerate() {
                let mut ws = tungstenite::accept(stream.unwrap()).unwrap();
                if n == 0 {
                    ws.send(Message::Ping(vec![1, 2, 3].into())).unwrap();
                    ws.send(Message::Text(kline(T0 + 3 * STEP, true).into())).unwrap();
                    ws.send(Message::Text(kline(T0 + 4 * STEP, false).into())).unwrap();
                    ws.send(Message::Text("garbage".into())).unwrap();
                    if let Ok(Message::Pong(p)) = ws.read() {
                        assert_eq!(p, vec![1u8, 2, 3]);
                        *pongs2.lock().unwrap() += 1;
                    }
                    drop(ws); // avbrott utan stängning
                } else {
                    let _ = go_rx.recv_timeout(Duration::from_secs(5)); // börsen har fått stapel 4 och 5
                    ws.send(Message::Text(kline(T0 + 5 * STEP, true).into())).unwrap();
                    loop {
                        if ws.read().is_err() {
                            break;
                        }
                    }
                }
            }
        });

        let src = FakeSource::new(4, false); // stapel 0–3 finns hos "börsen"
        let src = WsSource { inner: src, url };
        let cfg = Config { warmup_bars: 10, stale_after_secs: 5, ..Config::default() };
        let status = Arc::new(Mutex::new(Status::new("binance", "spot", "BTCUSDT", "4h", ":memory:")));
        let seen = Arc::new(Mutex::new(Vec::<State>::new()));
        let seen2 = seen.clone();
        let stop = Arc::new(AtomicBool::new(false));
        let timing = Timing { backoff_base: Duration::from_millis(20), backoff_cap: Duration::from_millis(50), read_tick: Duration::from_millis(50), close_grace: Duration::from_secs(10 * 365 * 86400), ..Timing::default() };
        let fake_bars = Arc::new(src);
        // Börsen får stapel 4 och 5 medan anslutningen är nere.
        let runner_src: Box<dyn Source> = Box::new(ArcSource(fake_bars.clone()));
        let bars_seen = Arc::new(Mutex::new(Vec::<(&'static str, Option<i64>)>::new()));
        let bars_seen2 = bars_seen.clone();
        let runner = Runner::new(&cfg, runner_src, Store::memory(), status.clone(), Box::new(move |s| seen2.lock().unwrap().push(s.state)), stop.clone(), timing)
            .with_bar_listener(Box::new(move |e| bars_seen2.lock().unwrap().push((e.kind, e.bar.map(|b| b.open_time)))));
        let probe = status.clone();
        let handle = std::thread::spawn(move || runner.run());

        let wait_for = |cond: &dyn Fn(&Status) -> bool| {
            let end = Instant::now() + Duration::from_secs(10);
            while Instant::now() < end {
                if cond(&probe.lock().unwrap()) {
                    return true;
                }
                std::thread::sleep(Duration::from_millis(20));
            }
            false
        };
        assert!(wait_for(&|s| s.live_open_time == Some(T0 + 4 * STEP)), "live bar 4 from the stream");
        {
            let mut b = fake_bars.inner.bars.lock().unwrap();
            b.push(test_bar(T0 + 4 * STEP, STEP));
            b.push(test_bar(T0 + 5 * STEP, STEP));
        }
        go_tx.send(()).unwrap();
        assert!(wait_for(&|s| s.reconnects >= 1 && s.last_closed_open_time == Some(T0 + 5 * STEP) && s.closed_bars == 6 && s.gaps.is_empty()),
            "after the drop: reconnect, bar 4 from REST, bar 5 from the stream: {:?}", probe.lock().unwrap());
        assert!(probe.lock().unwrap().rejected >= 1, "garbage message counted");
        assert_eq!(*pongs.lock().unwrap(), 1, "ping answered with the same payload");
        stop.store(true, Ordering::SeqCst);
        handle.join().unwrap();
        let states = seen.lock().unwrap().clone();
        assert_eq!(states.last(), Some(&State::Stopped));
        assert!(states.contains(&State::Reconnecting) && states.contains(&State::Connected), "{states:?}");
        let bars = bars_seen.lock().unwrap().clone();
        assert!(bars.contains(&("live", Some(T0 + 4 * STEP))), "live update reaches the charts: {bars:?}");
        // Stapel 5 når diagrammen antingen som "closed" från strömmen eller, om REST-ikappkörningen efter
        // återanslutningen hann först, som en "resync" efter live-stapel 4 (strömmens kopia är då en dubblett).
        let live4 = bars.iter().position(|e| *e == ("live", Some(T0 + 4 * STEP))).unwrap();
        assert!(bars.contains(&("closed", Some(T0 + 5 * STEP))) || bars[live4..].iter().any(|(k, _)| *k == "resync"),
            "new closed bar reaches the charts: {bars:?}");
        assert!(bars.iter().any(|(k, _)| *k == "resync"), "REST catch-up tells the charts to reload: {bars:?}");
        assert!(!bars.contains(&("closed", Some(T0 + 3 * STEP))), "a repeated closed bar is not sent again: {bars:?}");
    }

    struct ArcSource(Arc<WsSource>);
    impl Source for ArcSource {
        fn name(&self) -> &'static str { self.0.name() }
        fn server_time(&self) -> Result<i64, SourceError> { self.0.server_time() }
        fn klines(&self, s: &str, i: &str, st: i64, l: usize, n: i64) -> Result<Vec<crate::market::source::SourceBar>, SourceError> { self.0.klines(s, i, st, l, n) }
        fn stream_url(&self, s: &str, i: &str) -> String { self.0.stream_url(s, i) }
        fn parse_stream(&self, t: &str) -> Result<StreamMsg, String> { self.0.parse_stream(t) }
        fn stream_period(&self) -> Duration { self.0.stream_period() }
    }

    #[test]
    fn a_silent_stream_is_marked_stale_then_recovers() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let url = format!("ws://{}", listener.local_addr().unwrap());
        // Anslutning 1 säger ingenting. Anslutning 2 skickar en pågående stapel.
        std::thread::spawn(move || {
            for (n, stream) in listener.incoming().enumerate() {
                let mut ws = tungstenite::accept(stream.unwrap()).unwrap();
                if n > 0 {
                    ws.send(Message::Text(kline(T0 + 3 * STEP, false).into())).unwrap();
                }
                while ws.read().is_ok() {}
            }
        });
        let src = WsSource { inner: FakeSource::new(3, false), url };
        let cfg = Config { warmup_bars: 10, stale_after_secs: 5, ..Config::default() };
        let status = Arc::new(Mutex::new(Status::new("binance", "spot", "BTCUSDT", "4h", ":memory:")));
        let seen = Arc::new(Mutex::new(Vec::<State>::new()));
        let seen2 = seen.clone();
        let stop = Arc::new(AtomicBool::new(false));
        let timing = Timing { backoff_base: Duration::from_millis(20), backoff_cap: Duration::from_millis(40), read_tick: Duration::from_millis(50), close_grace: Duration::from_secs(10 * 365 * 86400), ..Timing::default() };
        let mut runner = Runner::new(&cfg, Box::new(src), Store::memory(), status.clone(), Box::new(move |s| seen2.lock().unwrap().push(s.state)), stop.clone(), timing);
        runner.stale_after = Duration::from_millis(300); // snabbare än i drift
        let handle = std::thread::spawn(move || runner.run());
        let end = Instant::now() + Duration::from_secs(10);
        while Instant::now() < end && status.lock().unwrap().live_open_time != Some(T0 + 3 * STEP) {
            std::thread::sleep(Duration::from_millis(20));
        }
        stop.store(true, Ordering::SeqCst);
        handle.join().unwrap();
        let states = seen.lock().unwrap().clone();
        let stale_at = states.iter().position(|s| *s == State::Stale).expect("stale");
        assert!(states[stale_at..].contains(&State::Connected), "recovers after stale: {states:?}");
        assert_eq!(status.lock().unwrap().live_open_time, Some(T0 + 3 * STEP));
    }
}
