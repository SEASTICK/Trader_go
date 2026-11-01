//! SQLite i appens datamapp. Varje skrivning är en transaktion, och nyckeln
//! (leverantör, marknad, symbol, tidsram, öppningstid) gör att samma stapel aldrig sparas två gånger.
//! En redan sparad stängd stapel skrivs aldrig över: avvikande värden sparas som en rättelse.

use super::model::{Bar, SeriesKey};
use rusqlite::{params, Connection, OptionalExtension};
use std::path::Path;

pub const SCHEMA: &str = include_str!("schema.sql");
const SCHEMA_VERSION: &str = "1";
/// Hämtningsloggen behåller så här många rader (äldre tas bort vid varje ny rad).
pub const LOG_RETENTION_ROWS: i64 = 5_000;

pub struct Store {
    conn: Connection,
}

#[derive(Debug, Default, Clone, Copy, PartialEq)]
pub struct InsertStats {
    pub inserted: usize,
    pub duplicates: usize,
    pub corrections: usize,
}

impl Store {
    pub fn open(path: &Path) -> rusqlite::Result<Store> {
        let conn = Connection::open(path)?;
        conn.busy_timeout(std::time::Duration::from_secs(5))?;
        conn.pragma_update(None, "journal_mode", "WAL")?;
        conn.pragma_update(None, "synchronous", "NORMAL")?;
        Self::init(conn)
    }

    #[cfg(test)]
    pub fn memory() -> Store {
        Self::init(Connection::open_in_memory().unwrap()).unwrap()
    }

    fn init(conn: Connection) -> rusqlite::Result<Store> {
        conn.execute_batch(SCHEMA)?;
        conn.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?1)",
            [SCHEMA_VERSION],
        )?;
        Ok(Store { conn })
    }

    #[cfg(test)]
    pub fn conn(&self) -> &Connection {
        &self.conn
    }

    /// Sparar stängda, redan kontrollerade staplar i en enda transaktion. Allt eller inget.
    pub fn insert_closed(
        &mut self,
        k: &SeriesKey,
        bars: &[Bar],
        source: &str,
        event_time: Option<i64>,
        received_at: i64,
    ) -> rusqlite::Result<InsertStats> {
        let tx = self.conn.transaction()?;
        let mut stats = InsertStats::default();
        for b in bars {
            let stored: Option<Bar> = tx
                .query_row(
                    "SELECT open_time, open, high, low, close, volume, close_time FROM bars
                     WHERE provider=?1 AND market=?2 AND symbol=?3 AND interval=?4 AND open_time=?5",
                    params![k.provider, k.market, k.symbol, k.interval, b.open_time],
                    row_to_bar,
                )
                .optional()?;
            match stored {
                None => {
                    tx.execute(
                        "INSERT INTO bars (provider, market, symbol, interval, open_time, open, high, low, close, volume,
                                           close_time, source, event_time, received_at)
                         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
                        params![k.provider, k.market, k.symbol, k.interval, b.open_time, b.open, b.high, b.low,
                                b.close, b.volume, b.close_time, source, event_time, received_at],
                    )?;
                    stats.inserted += 1;
                }
                Some(old) if old == *b => stats.duplicates += 1,
                Some(old) => {
                    let n = tx.execute(
                        "INSERT OR IGNORE INTO corrections (provider, market, symbol, interval, open_time, stored, incoming,
                                                            source, detected_at)
                         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
                        params![k.provider, k.market, k.symbol, k.interval, b.open_time,
                                serde_json::to_string(&old).unwrap(), serde_json::to_string(b).unwrap(), source,
                                received_at],
                    )?;
                    stats.corrections += n;
                    stats.duplicates += 1 - n;
                }
            }
        }
        tx.commit()?;
        Ok(stats)
    }

    pub fn set_live(
        &mut self,
        k: &SeriesKey,
        b: &Bar,
        event_time: Option<i64>,
        received_at: i64,
    ) -> rusqlite::Result<()> {
        self.conn.execute(
            "INSERT INTO live_bar (provider, market, symbol, interval, open_time, open, high, low, close, volume,
                                   close_time, event_time, received_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)
             ON CONFLICT (provider, market, symbol, interval) DO UPDATE SET
               open_time=excluded.open_time, open=excluded.open, high=excluded.high, low=excluded.low,
               close=excluded.close, volume=excluded.volume, close_time=excluded.close_time,
               event_time=excluded.event_time, received_at=excluded.received_at",
            params![k.provider, k.market, k.symbol, k.interval, b.open_time, b.open, b.high, b.low, b.close,
                    b.volume, b.close_time, event_time, received_at],
        )?;
        Ok(())
    }

    pub fn live(&self, k: &SeriesKey) -> rusqlite::Result<Option<Bar>> {
        self.conn
            .query_row(
                "SELECT open_time, open, high, low, close, volume, close_time FROM live_bar
                 WHERE provider=?1 AND market=?2 AND symbol=?3 AND interval=?4",
                params![k.provider, k.market, k.symbol, k.interval],
                row_to_bar,
            )
            .optional()
    }

    pub fn clear_live(&mut self, k: &SeriesKey) -> rusqlite::Result<()> {
        self.conn.execute(
            "DELETE FROM live_bar WHERE provider=?1 AND market=?2 AND symbol=?3 AND interval=?4",
            params![k.provider, k.market, k.symbol, k.interval],
        )?;
        Ok(())
    }

    /// (första, sista, antal) stängda staplar i serien.
    pub fn range(&self, k: &SeriesKey) -> rusqlite::Result<(Option<i64>, Option<i64>, i64)> {
        self.conn.query_row(
            "SELECT MIN(open_time), MAX(open_time), COUNT(*) FROM bars
             WHERE provider=?1 AND market=?2 AND symbol=?3 AND interval=?4",
            params![k.provider, k.market, k.symbol, k.interval],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )
    }

    #[cfg(test)]
    pub fn closed(&self, k: &SeriesKey) -> rusqlite::Result<Vec<Bar>> {
        let mut st = self.conn.prepare(
            "SELECT open_time, open, high, low, close, volume, close_time FROM bars
             WHERE provider=?1 AND market=?2 AND symbol=?3 AND interval=?4 ORDER BY open_time",
        )?;
        let rows = st.query_map(
            params![k.provider, k.market, k.symbol, k.interval],
            row_to_bar,
        )?;
        rows.collect()
    }

    /// Saknade öppningstider mellan första och sista sparade stapel, som sammanhängande intervall
    /// (från, till, båda inklusive). Bekräftade luckor hos källan räknas inte.
    pub fn missing_ranges(&self, k: &SeriesKey, step: i64) -> rusqlite::Result<Vec<(i64, i64)>> {
        let mut st = self.conn.prepare(
            "SELECT open_time FROM bars WHERE provider=?1 AND market=?2 AND symbol=?3 AND interval=?4 ORDER BY open_time",
        )?;
        let times: Vec<i64> = st
            .query_map(params![k.provider, k.market, k.symbol, k.interval], |r| {
                r.get(0)
            })?
            .collect::<rusqlite::Result<_>>()?;
        let confirmed = self.confirmed_gaps(k)?;
        let mut out = Vec::new();
        for w in times.windows(2) {
            if w[1] - w[0] > step {
                let gap = (w[0] + step, w[1] - step);
                if !confirmed.iter().any(|(a, b)| *a <= gap.0 && gap.1 <= *b) {
                    out.push(gap);
                }
            }
        }
        Ok(out)
    }

    pub fn confirm_gap(
        &mut self,
        k: &SeriesKey,
        from: i64,
        to: i64,
        at: i64,
    ) -> rusqlite::Result<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO confirmed_gaps (provider, market, symbol, interval, from_open, to_open, confirmed_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![k.provider, k.market, k.symbol, k.interval, from, to, at],
        )?;
        Ok(())
    }

    pub fn confirmed_gaps(&self, k: &SeriesKey) -> rusqlite::Result<Vec<(i64, i64)>> {
        let mut st = self.conn.prepare(
            "SELECT from_open, to_open FROM confirmed_gaps WHERE provider=?1 AND market=?2 AND symbol=?3 AND interval=?4",
        )?;
        let rows = st.query_map(params![k.provider, k.market, k.symbol, k.interval], |r| {
            Ok((r.get(0)?, r.get(1)?))
        })?;
        rows.collect()
    }

    pub fn correction_count(&self, k: &SeriesKey) -> rusqlite::Result<i64> {
        self.conn.query_row(
            "SELECT COUNT(*) FROM corrections WHERE provider=?1 AND market=?2 AND symbol=?3 AND interval=?4",
            params![k.provider, k.market, k.symbol, k.interval],
            |r| r.get(0),
        )
    }

    /// En rad i hämtningsloggen. Loggen hålls under LOG_RETENTION_ROWS rader.
    pub fn log(
        &mut self,
        k: &SeriesKey,
        at: i64,
        kind: &str,
        detail: &str,
        quality: &str,
    ) -> rusqlite::Result<()> {
        let tx = self.conn.transaction()?;
        tx.execute(
            "INSERT INTO fetch_log (at, provider, market, symbol, interval, kind, detail, quality)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![at, k.provider, k.market, k.symbol, k.interval, kind, detail, quality],
        )?;
        tx.execute(
            "DELETE FROM fetch_log WHERE id <= (SELECT MAX(id) FROM fetch_log) - ?1",
            [LOG_RETENTION_ROWS],
        )?;
        tx.commit()
    }
}

fn row_to_bar(r: &rusqlite::Row) -> rusqlite::Result<Bar> {
    Ok(Bar {
        open_time: r.get(0)?,
        open: r.get(1)?,
        high: r.get(2)?,
        low: r.get(3)?,
        close: r.get(4)?,
        volume: r.get(5)?,
        close_time: r.get(6)?,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::market::model::{test_bar, Config};

    const STEP: i64 = 14_400_000;
    const T0: i64 = 1_793_520_000_000;

    #[test]
    fn repeated_inserts_store_each_bar_once() {
        let mut s = Store::memory();
        let k = Config::default().key();
        let bars: Vec<Bar> = (0..5).map(|i| test_bar(T0 + i * STEP, STEP)).collect();
        assert_eq!(
            s.insert_closed(&k, &bars, "rest", None, 1)
                .unwrap()
                .inserted,
            5
        );
        let again = s.insert_closed(&k, &bars, "stream", Some(2), 2).unwrap();
        assert_eq!(
            (again.inserted, again.duplicates, again.corrections),
            (0, 5, 0)
        );
        assert_eq!(s.range(&k).unwrap(), (Some(T0), Some(T0 + 4 * STEP), 5));
    }

    #[test]
    fn a_changed_closed_bar_is_kept_and_recorded_as_a_correction() {
        let mut s = Store::memory();
        let k = Config::default().key();
        let orig = test_bar(T0, STEP);
        s.insert_closed(&k, &[orig], "rest", None, 1).unwrap();
        let changed = Bar {
            close: 106.0,
            ..orig
        };
        let st = s.insert_closed(&k, &[changed], "rest", None, 2).unwrap();
        assert_eq!(st.corrections, 1);
        assert_eq!(
            s.closed(&k).unwrap(),
            vec![orig],
            "history is never changed silently"
        );
        assert_eq!(
            s.insert_closed(&k, &[changed], "rest", None, 3)
                .unwrap()
                .corrections,
            0,
            "recorded once"
        );
        assert_eq!(s.correction_count(&k).unwrap(), 1);
    }

    #[test]
    fn a_failing_batch_writes_nothing() {
        let mut s = Store::memory();
        let k = Config::default().key();
        s.conn()
            .execute_batch(&format!(
                "CREATE TRIGGER boom BEFORE INSERT ON bars WHEN NEW.open_time = {} BEGIN SELECT RAISE(ABORT, 'boom'); END;",
                T0 + 2 * STEP
            ))
            .unwrap();
        let bars: Vec<Bar> = (0..4).map(|i| test_bar(T0 + i * STEP, STEP)).collect();
        assert!(s.insert_closed(&k, &bars, "rest", None, 1).is_err());
        assert_eq!(s.range(&k).unwrap().2, 0, "the whole batch is rolled back");
    }

    #[test]
    fn gaps_are_found_and_confirmed_gaps_are_not_reported() {
        let mut s = Store::memory();
        let k = Config::default().key();
        let bars: Vec<Bar> = [0, 1, 4, 5, 7]
            .iter()
            .map(|i| test_bar(T0 + i * STEP, STEP))
            .collect();
        s.insert_closed(&k, &bars, "rest", None, 1).unwrap();
        assert_eq!(
            s.missing_ranges(&k, STEP).unwrap(),
            vec![
                (T0 + 2 * STEP, T0 + 3 * STEP),
                (T0 + 6 * STEP, T0 + 6 * STEP)
            ]
        );
        s.confirm_gap(&k, T0 + 2 * STEP, T0 + 3 * STEP, 9).unwrap();
        assert_eq!(
            s.missing_ranges(&k, STEP).unwrap(),
            vec![(T0 + 6 * STEP, T0 + 6 * STEP)]
        );
    }

    #[test]
    fn the_log_is_capped() {
        let mut s = Store::memory();
        let k = Config::default().key();
        for i in 0..(LOG_RETENTION_ROWS + 20) {
            s.log(&k, i, "rest", "x", "ok").unwrap();
        }
        let n: i64 = s
            .conn()
            .query_row("SELECT COUNT(*) FROM fetch_log", [], |r| r.get(0))
            .unwrap();
        assert!(n <= LOG_RETENTION_ROWS + 1, "{n} rows");
    }
}
