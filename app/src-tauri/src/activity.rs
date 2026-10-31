//! Tracks running paper sessions and backtests so an update never restarts the app under them.

use serde::Serialize;
use std::sync::atomic::{AtomicUsize, Ordering};

#[derive(Default)]
pub struct Activity {
    paper: AtomicUsize,
    backtest: AtomicUsize,
}

#[derive(Debug, Clone, Copy, Serialize, PartialEq)]
pub struct Counts {
    pub paper: usize,
    pub backtest: usize,
}

impl Activity {
    fn counter(&self, kind: &str) -> Result<&AtomicUsize, String> {
        match kind {
            "paper" => Ok(&self.paper),
            "backtest" => Ok(&self.backtest),
            _ => Err(format!("unknown activity '{kind}'")),
        }
    }

    pub fn start(&self, kind: &str) -> Result<Counts, String> {
        self.counter(kind)?.fetch_add(1, Ordering::SeqCst);
        Ok(self.counts())
    }

    pub fn stop(&self, kind: &str) -> Result<Counts, String> {
        let c = self.counter(kind)?;
        let _ = c.fetch_update(Ordering::SeqCst, Ordering::SeqCst, |n| n.checked_sub(1));
        Ok(self.counts())
    }

    pub fn counts(&self) -> Counts {
        Counts {
            paper: self.paper.load(Ordering::SeqCst),
            backtest: self.backtest.load(Ordering::SeqCst),
        }
    }

    /// Err with a user-facing reason while anything is running.
    pub fn ensure_idle(&self) -> Result<(), String> {
        let Counts { paper, backtest } = self.counts();
        if paper + backtest == 0 {
            return Ok(());
        }
        Err(format!(
            "Update is ready but waits until {paper} paper session(s) and {backtest} backtest(s) have finished."
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn install_is_deferred_while_running() {
        let a = Activity::default();
        assert!(a.ensure_idle().is_ok());
        a.start("paper").unwrap();
        a.start("backtest").unwrap();
        assert!(a.ensure_idle().is_err());
        a.stop("paper").unwrap();
        assert!(a.ensure_idle().is_err());
        a.stop("backtest").unwrap();
        assert!(a.ensure_idle().is_ok());
    }

    #[test]
    fn stop_never_underflows_and_kinds_are_checked() {
        let a = Activity::default();
        a.stop("paper").unwrap();
        assert_eq!(
            a.counts(),
            Counts {
                paper: 0,
                backtest: 0
            }
        );
        assert!(a.start("live").is_err());
    }
}
