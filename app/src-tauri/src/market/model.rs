//! Serie, stapel, konfiguration och kontrollerna som körs när en stapel tas emot.
//! Motorns `quality.check` är fortfarande facit för experiment; det här stoppar bara trasig data vid dörren.

use serde::{Deserialize, Serialize};

/// Tidsramar som både motorn (`engine/traderlab/bars.py`) och Binance stöder, med längd i ms.
pub const INTERVALS: &[(&str, i64)] = &[
    ("1m", 60_000),
    ("5m", 300_000),
    ("15m", 900_000),
    ("1h", 3_600_000),
    ("4h", 14_400_000),
    ("1d", 86_400_000),
];
/// Symboler som är provade. Fler läggs till här efter att de kontrollerats.
pub const SYMBOLS: &[&str] = &["BTCUSDT", "ETHUSDT"];

pub fn interval_ms(interval: &str) -> Option<i64> {
    INTERVALS.iter().find(|(i, _)| *i == interval).map(|(_, ms)| *ms)
}

/// En serie: leverantör, marknad, symbol och tidsram. Tillsammans med öppningstiden är det nyckeln.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct SeriesKey {
    pub provider: String,
    pub market: String,
    pub symbol: String,
    pub interval: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Bar {
    /// Öppningstid, ms UTC.
    pub open_time: i64,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
    /// Sista millisekunden i stapeln (Binance: open_time + längd - 1).
    pub close_time: i64,
}

/// Binance använder ms, men vissa källor ger mikrosekunder. Allt lagras i ms.
pub fn to_ms(ts: i64) -> i64 {
    if ts > 100_000_000_000_000 {
        ts / 1000
    } else {
        ts
    }
}

/// Mottagningskontroll: siffror, OHLC, tidsjustering och längd. Fel stapel sparas aldrig.
pub fn validate(bar: &Bar, step_ms: i64) -> Result<(), String> {
    let prices = [bar.open, bar.high, bar.low, bar.close];
    if prices.iter().chain([&bar.volume]).any(|v| !v.is_finite()) {
        return Err("värde som inte är ett tal".into());
    }
    if prices.iter().any(|p| *p <= 0.0) {
        return Err("pris noll eller negativt".into());
    }
    if bar.volume < 0.0 {
        return Err("negativ volym".into());
    }
    if bar.low > bar.open.min(bar.close) || bar.high < bar.open.max(bar.close) || bar.low > bar.high {
        return Err("high/low stämmer inte med open/close".into());
    }
    if bar.open_time.rem_euclid(step_ms) != 0 {
        return Err("öppningstiden ligger inte på tidsramen".into());
    }
    if bar.close_time != bar.open_time + step_ms - 1 {
        return Err("stängningstiden stämmer inte med tidsramen".into());
    }
    Ok(())
}

fn default_warmup() -> u32 {
    1000
}
fn default_stale() -> u64 {
    30
}

/// Läses från `market/config.json` i appens datamapp om filen finns, annars standard.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Config {
    pub provider: String,
    pub market: String,
    pub symbol: String,
    pub interval: String,
    /// Antal stängda staplar som hämtas bakåt vid första start. Inte en garanti för att det räcker för en
    /// strategi: när en strategi körs live ska behovet räknas ut från dess längsta fönster.
    #[serde(default = "default_warmup")]
    pub warmup_bars: u32,
    /// Utan meddelanden så här länge (strömmen skickar var 2:a sekund, servern pingar var 20:e) räknas
    /// anslutningen som död.
    #[serde(default = "default_stale")]
    pub stale_after_secs: u64,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            provider: "binance".into(),
            market: "spot".into(),
            symbol: "BTCUSDT".into(),
            interval: "4h".into(),
            warmup_bars: default_warmup(),
            stale_after_secs: default_stale(),
        }
    }
}

impl Config {
    pub fn validate(&self) -> Result<(), String> {
        if self.provider != "binance" {
            return Err(format!("okänd leverantör {}; stöds: binance", self.provider));
        }
        if self.market != "spot" {
            return Err(format!("okänd marknad {}; stöds: spot", self.market));
        }
        if !SYMBOLS.contains(&self.symbol.as_str()) {
            return Err(format!("symbolen {} stöds inte; stöds: {}", self.symbol, SYMBOLS.join(", ")));
        }
        if interval_ms(&self.interval).is_none() {
            let all: Vec<&str> = INTERVALS.iter().map(|(i, _)| *i).collect();
            return Err(format!("tidsramen {} stöds inte; stöds: {}", self.interval, all.join(", ")));
        }
        if !(1..=20_000).contains(&self.warmup_bars) {
            return Err("warmup_bars måste vara 1–20000".into());
        }
        if !(5..=600).contains(&self.stale_after_secs) {
            return Err("stale_after_secs måste vara 5–600".into());
        }
        Ok(())
    }

    pub fn key(&self) -> SeriesKey {
        SeriesKey {
            provider: self.provider.clone(),
            market: self.market.clone(),
            symbol: self.symbol.clone(),
            interval: self.interval.clone(),
        }
    }

    pub fn step_ms(&self) -> i64 {
        interval_ms(&self.interval).expect("validerad tidsram")
    }
}

/// En giltig stapel för tester i hela modulen.
#[cfg(test)]
pub fn test_bar(t: i64, step: i64) -> Bar {
    Bar { open_time: t, open: 100.0, high: 110.0, low: 90.0, close: 105.0, volume: 3.0, close_time: t + step - 1 }
}

#[cfg(test)]
mod tests {
    use super::*;
    use test_bar as bar;

    #[test]
    fn accepts_a_good_bar_and_rejects_broken_ones() {
        let step = 14_400_000;
        let ok = bar(1_793_520_000_000, step);
        assert!(validate(&ok, step).is_ok());
        for (b, why) in [
            (Bar { high: 101.0, ..ok }, "high under close"),
            (Bar { low: 0.0, ..ok }, "zero price"),
            (Bar { volume: -1.0, ..ok }, "negative volume"),
            (Bar { open: f64::NAN, ..ok }, "NaN"),
            (Bar { open_time: ok.open_time + 1, close_time: ok.close_time + 1, ..ok }, "misaligned"),
            (Bar { close_time: ok.close_time + 5, ..ok }, "wrong length"),
        ] {
            assert!(validate(&b, step).is_err(), "{why} should be rejected");
        }
    }

    #[test]
    fn microseconds_become_milliseconds() {
        assert_eq!(to_ms(1_793_520_000_000), 1_793_520_000_000);
        assert_eq!(to_ms(1_793_520_000_000_000), 1_793_520_000_000);
    }

    #[test]
    fn config_only_allows_supported_values() {
        assert!(Config::default().validate().is_ok());
        assert_eq!(Config::default().step_ms(), 14_400_000);
        for bad in [
            Config { symbol: "DOGEUSDT".into(), ..Config::default() },
            Config { interval: "2h".into(), ..Config::default() },
            Config { market: "um".into(), ..Config::default() },
            Config { warmup_bars: 0, ..Config::default() },
        ] {
            assert!(bad.validate().is_err());
        }
        assert!(serde_json::from_str::<Config>(r#"{"provider":"binance","market":"spot","symbol":"BTCUSDT","interval":"4h","apiKey":"x"}"#).is_err(),
            "unknown fields (like keys) are refused");
    }
}
