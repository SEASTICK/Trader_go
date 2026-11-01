//! Historik och ström utan glapp. Ren logik över `Source` och `Store`, utan trådar eller nät.
//!
//! Uppstart (se runner.rs): strömmen ansluts först, så att händelser under hämtningen väntar i
//! socketbufferten. Sedan `backfill` via REST från senaste sparade stängda stapel (eller uppvärmningen),
//! `fill_gaps`, och därefter läses strömmen. Överlapp tas bort av nyckeln i databasen.

use super::model::{validate, Bar, Config, SeriesKey};
use super::source::{Source, SourceError, KLINES_LIMIT};
use super::store::Store;

#[derive(Debug, Default, Clone, PartialEq)]
pub struct SyncReport {
    pub inserted: usize,
    pub duplicates: usize,
    pub corrections: usize,
    pub rejected: usize,
}

#[derive(Debug, PartialEq)]
pub enum Applied {
    Closed {
        inserted: bool,
    },
    Live,
    /// Äldre eller upprepad händelse; inget ändrades.
    Ignored,
    Rejected(String),
    /// En stängd stapel kom efter ett hopp: staplar däremellan saknas och ska hämtas via REST.
    GapDetected {
        from: i64,
        to: i64,
    },
}

#[derive(Debug)]
pub enum SyncError {
    Source(SourceError),
    Store(String),
}

impl From<SourceError> for SyncError {
    fn from(e: SourceError) -> Self {
        SyncError::Source(e)
    }
}
impl From<rusqlite::Error> for SyncError {
    fn from(e: rusqlite::Error) -> Self {
        SyncError::Store(e.to_string())
    }
}

impl std::fmt::Display for SyncError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            SyncError::Source(e) => write!(f, "{e}"),
            SyncError::Store(e) => write!(f, "lagringsfel: {e}"),
        }
    }
}

pub struct Sync {
    pub key: SeriesKey,
    pub step: i64,
    pub warmup_bars: u32,
}

impl Sync {
    pub fn new(cfg: &Config) -> Self {
        Sync {
            key: cfg.key(),
            step: cfg.step_ms(),
            warmup_bars: cfg.warmup_bars,
        }
    }

    fn align(&self, t: i64) -> i64 {
        t - t.rem_euclid(self.step)
    }

    /// Hämtar allt från `from` till nu via REST. Stängda staplar sparas, den öppna blir live-stapel.
    fn fetch_range(
        &self,
        src: &dyn Source,
        store: &mut Store,
        from: i64,
        until: Option<i64>,
        now_local: i64,
        rep: &mut SyncReport,
    ) -> Result<usize, SyncError> {
        let server_now = src.server_time()?;
        let mut start = from;
        let mut got = 0;
        loop {
            let page = src.klines(
                &self.key.symbol,
                &self.key.interval,
                start,
                KLINES_LIMIT,
                server_now,
            )?;
            let n = page.len();
            let mut closed = Vec::with_capacity(n);
            let mut last_seen = None;
            for sb in page {
                if sb.bar.open_time < start || until.is_some_and(|u| sb.bar.open_time > u) {
                    continue;
                }
                last_seen = Some(sb.bar.open_time);
                if let Err(why) = validate(&sb.bar, self.step) {
                    rep.rejected += 1;
                    store.log(
                        &self.key,
                        now_local,
                        "rejected",
                        &format!("rest {}: {why}", sb.bar.open_time),
                        "rejected",
                    )?;
                    continue;
                }
                if sb.closed {
                    closed.push(sb.bar);
                } else {
                    store.set_live(&self.key, &sb.bar, None, now_local)?;
                }
            }
            let st = store.insert_closed(&self.key, &closed, "rest", None, now_local)?;
            rep.inserted += st.inserted;
            rep.duplicates += st.duplicates;
            rep.corrections += st.corrections;
            got += closed.len();
            match last_seen {
                Some(t) if n >= KLINES_LIMIT && until.is_none_or(|u| t < u) => {
                    start = t + self.step
                }
                _ => break,
            }
        }
        Ok(got)
    }

    /// Hämtar det som saknas sedan förra gången (eller uppvärmningen vid första start).
    pub fn backfill(
        &self,
        src: &dyn Source,
        store: &mut Store,
        now_local: i64,
    ) -> Result<SyncReport, SyncError> {
        let mut rep = SyncReport::default();
        let (_, last, _) = store.range(&self.key)?;
        let from = match last {
            Some(t) => t + self.step,
            None => self.align(now_local) - self.warmup_bars as i64 * self.step,
        };
        self.fetch_range(src, store, from, None, now_local, &mut rep)?;
        let detail = format!(
            "backfill från {from}: {} nya, {} dubbletter, {} rättelser, {} avvisade",
            rep.inserted, rep.duplicates, rep.corrections, rep.rejected
        );
        store.log(
            &self.key,
            now_local,
            "backfill",
            &detail,
            if rep.rejected + rep.corrections == 0 {
                "ok"
            } else {
                "warning"
            },
        )?;
        Ok(rep)
    }

    /// Försöker fylla varje lucka via REST. Det som källan själv saknar markeras som bekräftad lucka,
    /// aldrig ifyllt. Returnerar luckor som finns kvar.
    pub fn fill_gaps(
        &self,
        src: &dyn Source,
        store: &mut Store,
        now_local: i64,
    ) -> Result<Vec<(i64, i64)>, SyncError> {
        for (from, to) in store.missing_ranges(&self.key, self.step)? {
            let mut rep = SyncReport::default();
            self.fetch_range(src, store, from, Some(to), now_local, &mut rep)?;
            store.log(
                &self.key,
                now_local,
                "gap",
                &format!("lucka {from}–{to}: {} hämtade", rep.inserted),
                "warning",
            )?;
        }
        // Det som fortfarande saknas efter ett lyckat REST-svar finns inte hos källan.
        for (from, to) in store.missing_ranges(&self.key, self.step)? {
            store.confirm_gap(&self.key, from, to, now_local)?;
            store.log(
                &self.key,
                now_local,
                "gap",
                &format!("lucka {from}–{to} saknas hos källan; lämnas tom"),
                "gap",
            )?;
        }
        Ok(store.missing_ranges(&self.key, self.step)?)
    }

    /// En händelse från strömmen.
    pub fn apply(
        &self,
        store: &mut Store,
        bar: &Bar,
        closed: bool,
        event_time: i64,
        received_at: i64,
    ) -> Result<Applied, SyncError> {
        if let Err(why) = validate(bar, self.step) {
            store.log(
                &self.key,
                received_at,
                "rejected",
                &format!("stream {}: {why}", bar.open_time),
                "rejected",
            )?;
            return Ok(Applied::Rejected(why));
        }
        let (_, last, _) = store.range(&self.key)?;
        if closed {
            if let Some(l) = last {
                if bar.open_time > l + self.step {
                    store.insert_closed(
                        &self.key,
                        &[*bar],
                        "stream",
                        Some(event_time),
                        received_at,
                    )?;
                    return Ok(Applied::GapDetected {
                        from: l + self.step,
                        to: bar.open_time - self.step,
                    });
                }
            }
            let st =
                store.insert_closed(&self.key, &[*bar], "stream", Some(event_time), received_at)?;
            if store
                .live(&self.key)?
                .is_some_and(|lb| lb.open_time <= bar.open_time)
            {
                store.clear_live(&self.key)?;
            }
            return Ok(if st.inserted == 0 && st.corrections == 0 {
                Applied::Ignored
            } else {
                Applied::Closed {
                    inserted: st.inserted > 0,
                }
            });
        }
        // Pågående stapel: bara om den är nyare än allt stängt och inte äldre än nuvarande live-stapel.
        if last.is_some_and(|l| bar.open_time <= l)
            || store
                .live(&self.key)?
                .is_some_and(|lb| bar.open_time < lb.open_time)
        {
            return Ok(Applied::Ignored);
        }
        store.set_live(&self.key, bar, Some(event_time), received_at)?;
        Ok(Applied::Live)
    }
}

#[cfg(test)]
pub mod tests {
    use super::*;
    use crate::market::model::test_bar;
    use crate::market::source::{SourceBar, StreamMsg};
    use std::sync::Mutex;
    use std::time::Duration;

    pub const STEP: i64 = 14_400_000;
    pub const T0: i64 = 1_793_520_000_000; // 2026-11-01 08:00 UTC, på 4h-rutnätet

    /// En påhittad börs: har staplarna i `bars`; den sista är öppen om `open_last`.
    pub struct FakeSource {
        pub bars: Mutex<Vec<Bar>>,
        pub open_last: bool,
        pub now: i64,
        pub calls: Mutex<Vec<i64>>,
        pub fail_next: Mutex<Option<SourceError>>,
    }

    impl FakeSource {
        pub fn new(n: i64, open_last: bool) -> Self {
            let bars = (0..n).map(|i| test_bar(T0 + i * STEP, STEP)).collect();
            FakeSource {
                bars: Mutex::new(bars),
                open_last,
                now: T0 + n * STEP - 1000,
                calls: Mutex::new(vec![]),
                fail_next: Mutex::new(None),
            }
        }
    }

    impl Source for FakeSource {
        fn name(&self) -> &'static str {
            "binance"
        }
        fn server_time(&self) -> Result<i64, SourceError> {
            match self.fail_next.lock().unwrap().take() {
                Some(e) => Err(e),
                None => Ok(self.now),
            }
        }
        fn klines(
            &self,
            _: &str,
            _: &str,
            start: i64,
            limit: usize,
            _: i64,
        ) -> Result<Vec<SourceBar>, SourceError> {
            self.calls.lock().unwrap().push(start);
            let bars = self.bars.lock().unwrap();
            let last = bars.last().map(|b| b.open_time);
            Ok(bars
                .iter()
                .filter(|b| b.open_time >= start)
                .take(limit)
                .map(|b| SourceBar {
                    bar: *b,
                    closed: !(self.open_last && Some(b.open_time) == last),
                })
                .collect())
        }
        fn stream_url(&self, _: &str, _: &str) -> String {
            String::new()
        }
        fn parse_stream(&self, _: &str) -> Result<StreamMsg, String> {
            Ok(StreamMsg::Other)
        }
        fn stream_period(&self) -> Duration {
            Duration::from_secs(2)
        }
    }

    fn sync(warmup: u32) -> Sync {
        Sync::new(&Config {
            warmup_bars: warmup,
            ..Config::default()
        })
    }

    fn times(store: &Store, s: &Sync) -> Vec<i64> {
        store
            .closed(&s.key)
            .unwrap()
            .iter()
            .map(|b| (b.open_time - T0) / STEP)
            .collect()
    }

    #[test]
    fn warmup_takes_only_closed_bars_and_keeps_the_open_one_live() {
        let src = FakeSource::new(10, true);
        let s = sync(5);
        let mut store = Store::memory();
        let rep = s.backfill(&src, &mut store, src.now).unwrap();
        assert_eq!(
            times(&store, &s),
            vec![4, 5, 6, 7, 8],
            "5 warmup bars, the open 9th is not analysis data"
        );
        assert_eq!(rep.inserted, 5);
        assert_eq!(
            store
                .live(&s.key)
                .unwrap()
                .map(|b| (b.open_time - T0) / STEP),
            Some(9)
        );
    }

    #[test]
    fn history_and_stream_overlap_without_loss_or_duplicates() {
        let src = FakeSource::new(10, true);
        let s = sync(20);
        let mut store = Store::memory();
        s.backfill(&src, &mut store, src.now).unwrap();
        // Buffrade händelser under hämtningen: en upprepning av en sparad stapel, stängningen av den öppna,
        // och nästa stapel som pågår.
        let b8 = test_bar(T0 + 8 * STEP, STEP);
        let b9 = test_bar(T0 + 9 * STEP, STEP);
        let b10 = test_bar(T0 + 10 * STEP, STEP);
        assert_eq!(
            s.apply(&mut store, &b8, true, 1, 1).unwrap(),
            Applied::Ignored
        );
        assert_eq!(
            s.apply(&mut store, &b9, true, 2, 2).unwrap(),
            Applied::Closed { inserted: true }
        );
        assert_eq!(
            s.apply(&mut store, &b10, false, 3, 3).unwrap(),
            Applied::Live
        );
        assert_eq!(
            s.apply(&mut store, &b9, true, 4, 4).unwrap(),
            Applied::Ignored,
            "repeated message"
        );
        assert_eq!(times(&store, &s), (0..=9).collect::<Vec<_>>());
        assert_eq!(
            store.live(&s.key).unwrap().unwrap().open_time,
            b10.open_time
        );
    }

    #[test]
    fn out_of_order_and_broken_events_change_nothing() {
        let src = FakeSource::new(6, false);
        let s = sync(20);
        let mut store = Store::memory();
        s.backfill(&src, &mut store, src.now).unwrap();
        let live = test_bar(T0 + 6 * STEP, STEP);
        s.apply(&mut store, &live, false, 10, 10).unwrap();
        assert_eq!(
            s.apply(&mut store, &test_bar(T0 + 2 * STEP, STEP), false, 9, 9)
                .unwrap(),
            Applied::Ignored,
            "old live update"
        );
        assert!(matches!(
            s.apply(&mut store, &Bar { high: 1.0, ..live }, false, 11, 11)
                .unwrap(),
            Applied::Rejected(_)
        ));
        assert!(matches!(
            s.apply(
                &mut store,
                &Bar {
                    open_time: live.open_time + 7,
                    ..live
                },
                true,
                12,
                12
            )
            .unwrap(),
            Applied::Rejected(_)
        ));
        assert_eq!(times(&store, &s), (0..6).collect::<Vec<_>>());
        assert_eq!(store.live(&s.key).unwrap().unwrap(), live);
    }

    #[test]
    fn a_jump_in_the_stream_is_detected_and_filled_from_rest() {
        let src = FakeSource::new(5, false);
        let s = sync(20);
        let mut store = Store::memory();
        s.backfill(&src, &mut store, src.now).unwrap();
        // Datorn sov: börsen har gått vidare tre staplar.
        {
            let mut b = src.bars.lock().unwrap();
            for i in 5..9 {
                b.push(test_bar(T0 + i * STEP, STEP));
            }
        }
        let applied = s
            .apply(&mut store, &test_bar(T0 + 8 * STEP, STEP), true, 1, 1)
            .unwrap();
        assert_eq!(
            applied,
            Applied::GapDetected {
                from: T0 + 5 * STEP,
                to: T0 + 7 * STEP
            }
        );
        assert_eq!(s.fill_gaps(&src, &mut store, src.now).unwrap(), vec![]);
        assert_eq!(times(&store, &s), (0..9).collect::<Vec<_>>());
    }

    #[test]
    fn a_gap_the_source_itself_has_is_confirmed_not_invented() {
        let src = FakeSource::new(8, false);
        src.bars
            .lock()
            .unwrap()
            .retain(|b| b.open_time != T0 + 3 * STEP && b.open_time != T0 + 4 * STEP);
        let s = sync(20);
        let mut store = Store::memory();
        s.backfill(&src, &mut store, src.now).unwrap();
        assert_eq!(
            store.missing_ranges(&s.key, STEP).unwrap(),
            vec![(T0 + 3 * STEP, T0 + 4 * STEP)]
        );
        assert_eq!(
            s.fill_gaps(&src, &mut store, src.now).unwrap(),
            vec![],
            "confirmed at the source"
        );
        assert_eq!(
            store.confirmed_gaps(&s.key).unwrap(),
            vec![(T0 + 3 * STEP, T0 + 4 * STEP)]
        );
        assert_eq!(
            times(&store, &s),
            vec![0, 1, 2, 5, 6, 7],
            "nothing is filled in"
        );
    }

    #[test]
    fn restart_resumes_from_the_saved_position() {
        let src = FakeSource::new(5, false);
        let s = sync(20);
        let mut store = Store::memory();
        s.backfill(&src, &mut store, src.now).unwrap();
        {
            let mut b = src.bars.lock().unwrap();
            b.push(test_bar(T0 + 5 * STEP, STEP));
            b.push(test_bar(T0 + 6 * STEP, STEP));
        }
        src.calls.lock().unwrap().clear();
        let rep = s.backfill(&src, &mut store, src.now).unwrap();
        assert_eq!(
            *src.calls.lock().unwrap(),
            vec![T0 + 5 * STEP],
            "asks only for what is missing"
        );
        assert_eq!(rep.inserted, 2);
        assert_eq!(rep.duplicates, 0);
    }

    #[test]
    fn long_histories_are_paged() {
        let src = FakeSource::new(2500, true); // som i verkligheten: stapeln som pågår nu är öppen
        let s = sync(2400);
        let mut store = Store::memory();
        s.backfill(&src, &mut store, src.now).unwrap();
        assert_eq!(store.range(&s.key).unwrap().2, 2400);
        assert_eq!(src.calls.lock().unwrap().len(), 3);
    }

    #[test]
    fn source_errors_are_returned_not_swallowed() {
        let src = FakeSource::new(5, false);
        *src.fail_next.lock().unwrap() = Some(SourceError::RateLimited {
            retry_after_secs: 9,
            banned: false,
        });
        let mut store = Store::memory();
        assert!(matches!(
            sync(5).backfill(&src, &mut store, src.now),
            Err(SyncError::Source(SourceError::RateLimited {
                retry_after_secs: 9,
                ..
            }))
        ));
        assert_eq!(store.range(&sync(5).key).unwrap().2, 0);
    }
}
