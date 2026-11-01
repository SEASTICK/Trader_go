//! Datakällor. Allt leverantörsspecifikt ligger bakom `Source`, så att fler källor kan läggas till.
//! Binance används bara via de rena marknadsdataadresserna: inga konton, inga nycklar, inga order.

use super::model::{to_ms, Bar};
use std::time::Duration;

/// Bara publik marknadsdata (https://developers.binance.com/docs/binance-spot-api-docs/faqs/market_data_only).
pub const BINANCE_REST: &str = "https://data-api.binance.vision";
pub const BINANCE_STREAM: &str = "wss://data-stream.binance.vision:443";
/// Max staplar per anrop enligt dokumentationen för GET /api/v3/klines (vikt 2).
pub const KLINES_LIMIT: usize = 1000;
/// Pausa REST när den använda vikten närmar sig gränsen (6000 per minut enligt exchangeInfo).
const WEIGHT_PAUSE_AT: u32 = 4800;

#[derive(Debug, Clone, PartialEq)]
pub enum SourceError {
    /// 429 eller 418. Väntetiden kommer från Retry-After.
    RateLimited { retry_after_secs: u64, banned: bool },
    Network(String),
    Invalid(String),
}

impl std::fmt::Display for SourceError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            SourceError::RateLimited { retry_after_secs, banned: false } => write!(f, "för många anrop, väntar {retry_after_secs} s"),
            SourceError::RateLimited { retry_after_secs, banned: true } => write!(f, "tillfälligt avstängd av källan (418), väntar {retry_after_secs} s"),
            SourceError::Network(e) => write!(f, "nätverksfel: {e}"),
            SourceError::Invalid(e) => write!(f, "oväntat svar: {e}"),
        }
    }
}

/// En stapel från källan, med uppgift om den är stängd.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SourceBar {
    pub bar: Bar,
    pub closed: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub enum StreamMsg {
    Kline { bar: Bar, closed: bool, event_time: i64, symbol: String, interval: String },
    /// Källan stänger snart (planerat). Anslut på nytt.
    Shutdown,
    Other,
}

pub trait Source: Send {
    fn name(&self) -> &'static str;
    fn server_time(&self) -> Result<i64, SourceError>;
    /// Staplar från och med `start_ms`, högst `limit`. Den sista kan vara öppen.
    fn klines(&self, symbol: &str, interval: &str, start_ms: i64, limit: usize, server_now: i64) -> Result<Vec<SourceBar>, SourceError>;
    fn stream_url(&self, symbol: &str, interval: &str) -> String;
    fn parse_stream(&self, text: &str) -> Result<StreamMsg, String>;
    /// Hur ofta strömmen skickar meddelanden (används för att bedöma om den tystnat).
    fn stream_period(&self) -> Duration;
}

pub struct HttpResponse {
    pub status: u16,
    pub retry_after: Option<u64>,
    pub used_weight_1m: Option<u32>,
    pub body: String,
}

pub trait Http: Send {
    fn get(&self, url: &str) -> Result<HttpResponse, String>;
}

/// HTTPS med operativsystemets TLS (macOS Security, Windows SChannel).
pub struct UreqHttp {
    agent: ureq::Agent,
}

impl UreqHttp {
    pub fn new() -> Result<Self, String> {
        let tls = native_tls::TlsConnector::new().map_err(|e| e.to_string())?;
        let agent = ureq::AgentBuilder::new()
            .tls_connector(std::sync::Arc::new(tls))
            .timeout_connect(Duration::from_secs(10))
            .timeout(Duration::from_secs(30))
            .user_agent("TraderGO market data (paper only)")
            .build();
        Ok(UreqHttp { agent })
    }
}

impl Http for UreqHttp {
    fn get(&self, url: &str) -> Result<HttpResponse, String> {
        let resp = match self.agent.get(url).call() {
            Ok(r) => r,
            Err(ureq::Error::Status(_, r)) => r,
            Err(e) => return Err(e.to_string()),
        };
        let status = resp.status();
        let retry_after = resp.header("Retry-After").and_then(|v| v.trim().parse().ok());
        let used_weight_1m = resp.header("X-MBX-USED-WEIGHT-1M").and_then(|v| v.trim().parse().ok());
        let body = resp.into_string().map_err(|e| e.to_string())?;
        Ok(HttpResponse { status, retry_after, used_weight_1m, body })
    }
}

pub struct Binance<H: Http> {
    http: H,
    rest: String,
    stream: String,
}

impl<H: Http> Binance<H> {
    pub fn new(http: H) -> Self {
        Binance { http, rest: BINANCE_REST.into(), stream: BINANCE_STREAM.into() }
    }

    fn get_json(&self, path: &str) -> Result<serde_json::Value, SourceError> {
        let r = self.http.get(&format!("{}{path}", self.rest)).map_err(SourceError::Network)?;
        match r.status {
            200 => {}
            429 | 418 => {
                return Err(SourceError::RateLimited { retry_after_secs: r.retry_after.unwrap_or(60), banned: r.status == 418 })
            }
            s => return Err(SourceError::Network(format!("HTTP {s}: {}", r.body.chars().take(200).collect::<String>()))),
        }
        if r.used_weight_1m.is_some_and(|w| w >= WEIGHT_PAUSE_AT) {
            // Under gränsen än, men nära: vänta ut minuten hellre än att riskera 429.
            return Err(SourceError::RateLimited { retry_after_secs: 60, banned: false });
        }
        serde_json::from_str(&r.body).map_err(|e| SourceError::Invalid(e.to_string()))
    }
}

fn num(v: &serde_json::Value) -> Result<f64, String> {
    match v {
        serde_json::Value::String(s) => s.parse::<f64>().map_err(|e| format!("{s}: {e}")),
        serde_json::Value::Number(n) => n.as_f64().ok_or_else(|| "tal".into()),
        _ => Err(format!("väntade tal, fick {v}")),
    }
}

fn int(v: &serde_json::Value) -> Result<i64, String> {
    v.as_i64().ok_or_else(|| format!("väntade heltal, fick {v}"))
}

/// En rad från GET /api/v3/klines: [öppning, open, high, low, close, volym, stängning, …].
pub fn parse_rest_row(row: &serde_json::Value, server_now: i64) -> Result<SourceBar, String> {
    let a = row.as_array().filter(|a| a.len() >= 7).ok_or("rad med fel form")?;
    let bar = Bar {
        open_time: to_ms(int(&a[0])?),
        open: num(&a[1])?,
        high: num(&a[2])?,
        low: num(&a[3])?,
        close: num(&a[4])?,
        volume: num(&a[5])?,
        close_time: to_ms(int(&a[6])?),
    };
    // REST säger inte om stapeln är stängd; den är det när dess sista millisekund har passerat på servern.
    Ok(SourceBar { bar, closed: bar.close_time < server_now })
}

/// Ett meddelande från `<symbol>@kline_<interval>`.
pub fn parse_kline_event(text: &str) -> Result<StreamMsg, String> {
    let v: serde_json::Value = serde_json::from_str(text).map_err(|e| format!("inte JSON: {e}"))?;
    let v = v.get("data").unwrap_or(&v); // kombinerade strömmar packar in händelsen
    match v.get("e").and_then(|e| e.as_str()) {
        Some("kline") => {}
        Some("serverShutdown") => return Ok(StreamMsg::Shutdown),
        _ => return Ok(StreamMsg::Other),
    }
    let k = v.get("k").ok_or("kline saknar k")?;
    let field = |n: &str| k.get(n).ok_or_else(|| format!("kline saknar {n}"));
    let bar = Bar {
        open_time: to_ms(int(field("t")?)?),
        open: num(field("o")?)?,
        high: num(field("h")?)?,
        low: num(field("l")?)?,
        close: num(field("c")?)?,
        volume: num(field("v")?)?,
        close_time: to_ms(int(field("T")?)?),
    };
    Ok(StreamMsg::Kline {
        bar,
        closed: field("x")?.as_bool().ok_or("x är inte sant/falskt")?,
        event_time: to_ms(int(v.get("E").ok_or("saknar E")?)?),
        symbol: field("s")?.as_str().unwrap_or_default().to_string(),
        interval: field("i")?.as_str().unwrap_or_default().to_string(),
    })
}

impl<H: Http> Source for Binance<H> {
    fn name(&self) -> &'static str {
        "binance"
    }

    fn server_time(&self) -> Result<i64, SourceError> {
        let v = self.get_json("/api/v3/time")?;
        v.get("serverTime").and_then(|t| t.as_i64()).map(to_ms).ok_or_else(|| SourceError::Invalid("serverTime saknas".into()))
    }

    fn klines(&self, symbol: &str, interval: &str, start_ms: i64, limit: usize, server_now: i64) -> Result<Vec<SourceBar>, SourceError> {
        let v = self.get_json(&format!(
            "/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start_ms}&limit={}",
            limit.min(KLINES_LIMIT)
        ))?;
        let rows = v.as_array().ok_or_else(|| SourceError::Invalid("väntade en lista".into()))?;
        rows.iter().map(|r| parse_rest_row(r, server_now).map_err(SourceError::Invalid)).collect()
    }

    fn stream_url(&self, symbol: &str, interval: &str) -> String {
        format!("{}/ws/{}@kline_{interval}", self.stream, symbol.to_lowercase())
    }

    fn parse_stream(&self, text: &str) -> Result<StreamMsg, String> {
        parse_kline_event(text)
    }

    fn stream_period(&self) -> Duration {
        Duration::from_secs(2) // "Update Speed: 2000ms" för andra tidsramar än 1s
    }
}

#[cfg(test)]
pub mod fake {
    //! Inspelade och påhittade svar för tester, utan nät.
    use super::*;
    use std::collections::VecDeque;
    use std::sync::{Arc, Mutex};

    #[derive(Clone, Default)]
    pub struct FakeHttp {
        pub responses: Arc<Mutex<VecDeque<Result<HttpResponse, String>>>>,
        pub requests: Arc<Mutex<Vec<String>>>,
    }

    impl FakeHttp {
        pub fn push(&self, status: u16, body: &str, retry_after: Option<u64>) {
            self.responses.lock().unwrap().push_back(Ok(HttpResponse { status, retry_after, used_weight_1m: Some(2), body: body.into() }));
        }
        pub fn push_err(&self, e: &str) {
            self.responses.lock().unwrap().push_back(Err(e.into()));
        }
    }

    impl Http for FakeHttp {
        fn get(&self, url: &str) -> Result<HttpResponse, String> {
            self.requests.lock().unwrap().push(url.to_string());
            self.responses.lock().unwrap().pop_front().unwrap_or_else(|| Err("inget svar inspelat".into()))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::fake::FakeHttp;
    use super::*;

    /// Inspelat 2026-11-01 från https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=3
    /// (serverTime 1793534641277). Sista stapeln var fortfarande öppen.
    pub const RECORDED_REST: &str = r#"[[1793505600000,"77802.01000000","78068.00000000","77721.14000000","77991.28000000","1276.36281000",1793519999999,"0",1,"0","0","0"],[1793520000000,"77991.28000000","78285.00000000","77913.66000000","77962.62000000","1374.30554000",1793534399999,"0",1,"0","0","0"],[1793534400000,"77962.63000000","78025.53000000","77962.62000000","78013.03000000","19.35280000",1793548799999,"0",1,"0","0","0"]]"#;
    pub const RECORDED_SERVER_TIME: i64 = 1_793_534_641_277;

    #[test]
    fn rest_rows_parse_and_only_finished_bars_are_closed() {
        let http = FakeHttp::default();
        http.push(200, RECORDED_REST, None);
        let b = Binance::new(http.clone());
        let bars = b.klines("BTCUSDT", "4h", 1_793_505_600_000, 3, RECORDED_SERVER_TIME).unwrap();
        assert_eq!(bars.len(), 3);
        assert_eq!(bars[0].bar.open_time, 1_793_505_600_000);
        assert_eq!(bars[1].bar.close, 77962.62);
        assert_eq!(bars.iter().map(|b| b.closed).collect::<Vec<_>>(), vec![true, true, false]);
        let url = &http.requests.lock().unwrap()[0];
        assert!(url.starts_with("https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=4h&startTime=1793505600000"), "{url}");
    }

    #[test]
    fn stream_events_parse_closed_open_and_shutdown() {
        let open = r#"{"e":"kline","E":1793534650000,"s":"BTCUSDT","k":{"t":1793534400000,"T":1793548799999,"s":"BTCUSDT","i":"4h","f":1,"L":2,"o":"77962.63","c":"78013.03","h":"78025.53","l":"77962.62","v":"19.3528","n":10,"x":false,"q":"0","V":"0","Q":"0","B":"0"}}"#;
        match parse_kline_event(open).unwrap() {
            StreamMsg::Kline { closed, event_time, bar, interval, .. } => {
                assert!(!closed);
                assert_eq!(event_time, 1_793_534_650_000);
                assert_eq!(bar.close_time, 1_793_548_799_999);
                assert_eq!(interval, "4h");
            }
            m => panic!("{m:?}"),
        }
        let us = open.replace("1793534650000", "1793534650000000").replace("\"x\":false", "\"x\":true");
        assert!(matches!(parse_kline_event(&us).unwrap(), StreamMsg::Kline { closed: true, event_time: 1_793_534_650_000, .. }), "µs → ms");
        assert_eq!(parse_kline_event(r#"{"e":"serverShutdown","E":1}"#).unwrap(), StreamMsg::Shutdown);
        assert_eq!(parse_kline_event(r#"{"result":null,"id":1}"#).unwrap(), StreamMsg::Other);
        for bad in ["not json", r#"{"e":"kline","E":1,"k":{"t":1}}"#, r#"{"e":"kline","E":1,"k":{"t":1,"T":2,"o":"x","c":"1","h":"1","l":"1","v":"1","x":false,"s":"B","i":"4h"}}"#] {
            assert!(parse_kline_event(bad).is_err(), "{bad}");
        }
    }

    #[test]
    fn rate_limits_use_retry_after() {
        let http = FakeHttp::default();
        http.push(429, "{}", Some(7));
        http.push(418, "{}", Some(120));
        http.push_err("dns error");
        let b = Binance::new(http);
        assert_eq!(b.server_time(), Err(SourceError::RateLimited { retry_after_secs: 7, banned: false }));
        assert_eq!(b.server_time(), Err(SourceError::RateLimited { retry_after_secs: 120, banned: true }));
        assert!(matches!(b.server_time(), Err(SourceError::Network(_))));
    }

    #[test]
    fn only_public_market_data_hosts_are_used() {
        let b = Binance::new(FakeHttp::default());
        assert_eq!(b.stream_url("BTCUSDT", "4h"), "wss://data-stream.binance.vision:443/ws/btcusdt@kline_4h");
        assert!(BINANCE_REST.ends_with("data-api.binance.vision"));
    }

    /// Paper only: insamlingskoden får aldrig nå konto-, order- eller nyckeltjänster.
    #[test]
    fn no_account_order_or_key_code() {
        let sources = [include_str!("source.rs"), include_str!("runner.rs"), include_str!("sync.rs"), include_str!("store.rs"), include_str!("mod.rs")];
        let forbidden = ["/api/v3/order", "/api/v3/account", "userDataStream", "listenKey", "X-MBX-APIKEY", "signature=", "/sapi/", "api.binance.com", "stream.binance.com"];
        for src in sources {
            let code: String = src.lines().filter(|l| !l.contains("forbidden")).collect::<Vec<_>>().join("\n");
            for f in forbidden {
                assert!(!code.contains(f), "förbjuden sträng i insamlingskoden: {f}");
            }
        }
    }
}
