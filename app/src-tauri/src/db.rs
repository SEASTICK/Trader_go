//! Local SQLite store. Lives in the OS app-data folder, which updates never touch.
//!
//! Migrations are append-only. Each one runs inside a single transaction together with the
//! `user_version` bump, so a failed migration leaves the database exactly as it was. Before
//! migrating an existing database a copy is written to `backups/` for manual recovery.

use rusqlite::{params, Connection};
use serde::Serialize;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

/// Never edit or reorder an entry once released. Add a new one instead.
pub const MIGRATIONS: &[&str] = &[
    // 1: initial schema
    r#"
    CREATE TABLE settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE paper_trades (
        id               INTEGER PRIMARY KEY,
        opened_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
        symbol           TEXT NOT NULL,
        side             TEXT NOT NULL CHECK (side IN ('long', 'short')),
        quantity         REAL NOT NULL CHECK (quantity > 0),
        entry_price      REAL NOT NULL CHECK (entry_price > 0),
        exit_price       REAL,
        closed_at        TEXT,
        strategy_version TEXT,
        mode             TEXT NOT NULL DEFAULT 'paper' CHECK (mode = 'paper')
    );
    CREATE TABLE backtest_runs (
        id               INTEGER PRIMARY KEY,
        created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
        strategy_version TEXT NOT NULL,
        summary_json     TEXT NOT NULL,
        report_path      TEXT
    );
    "#,
];

const BACKUPS_KEPT: usize = 5;

#[derive(Debug, thiserror::Error)]
pub enum DbError {
    #[error("databasfel: {0}")]
    Sql(#[from] rusqlite::Error),
    #[error("filfel: {0}")]
    Io(#[from] std::io::Error),
    #[error(
        "databasen skapades av en nyare Trader_go (schema {found}, den här versionen klarar {supported}). \
         Installera senaste versionen; din data har inte ändrats"
    )]
    NewerSchema { found: usize, supported: usize },
}

pub fn open(path: &Path) -> Result<Connection, DbError> {
    migrate(path, MIGRATIONS)
}

pub fn migrate(path: &Path, migrations: &[&str]) -> Result<Connection, DbError> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;
    }
    let mut conn = Connection::open(path)?;
    conn.pragma_update(None, "journal_mode", "WAL")?;
    conn.pragma_update(None, "foreign_keys", "ON")?;

    let current = schema_version(&conn)?;
    let target = migrations.len();
    if current > target {
        return Err(DbError::NewerSchema {
            found: current,
            supported: target,
        });
    }
    if current == target {
        return Ok(conn);
    }
    if current > 0 {
        backup(&conn, path, &format!("schema{current}"))?;
    }

    let tx = conn.transaction()?;
    for sql in &migrations[current..] {
        tx.execute_batch(sql)?;
    }
    tx.pragma_update(None, "user_version", target as i64)?;
    tx.commit()?;
    Ok(conn)
}

pub fn schema_version(conn: &Connection) -> Result<usize, DbError> {
    let v: i64 = conn.query_row("PRAGMA user_version", [], |r| r.get(0))?;
    Ok(v as usize)
}

/// Copy taken right before the app installs an update, in case the new version misbehaves.
pub fn backup_before_update(conn: &Connection, path: &Path) -> Result<PathBuf, DbError> {
    backup(conn, path, "pre-update")
}

fn backup(conn: &Connection, path: &Path, label: &str) -> Result<PathBuf, DbError> {
    let dir = path.with_file_name("backups");
    std::fs::create_dir_all(&dir)?;
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let file = dir.join(format!("tradergo-{label}-{stamp}.db"));
    conn.execute("VACUUM INTO ?1", params![file.to_string_lossy()])?;
    prune_backups(&dir)?;
    Ok(file)
}

fn prune_backups(dir: &Path) -> Result<(), DbError> {
    let mut files: Vec<PathBuf> = std::fs::read_dir(dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|x| x == "db"))
        .collect();
    files.sort_by_key(|p| std::fs::metadata(p).and_then(|m| m.modified()).ok());
    while files.len() > BACKUPS_KEPT {
        std::fs::remove_file(files.remove(0))?;
    }
    Ok(())
}

#[derive(Debug, Serialize)]
pub struct PaperTrade {
    pub id: i64,
    pub opened_at: String,
    pub symbol: String,
    pub side: String,
    pub quantity: f64,
    pub entry_price: f64,
}

pub fn insert_paper_trade(
    conn: &Connection,
    symbol: &str,
    side: &str,
    quantity: f64,
    entry_price: f64,
) -> Result<i64, DbError> {
    conn.execute(
        "INSERT INTO paper_trades (symbol, side, quantity, entry_price) VALUES (?1, ?2, ?3, ?4)",
        params![symbol, side, quantity, entry_price],
    )?;
    Ok(conn.last_insert_rowid())
}

pub fn list_paper_trades(conn: &Connection, limit: u32) -> Result<Vec<PaperTrade>, DbError> {
    let mut stmt = conn.prepare(
        "SELECT id, opened_at, symbol, side, quantity, entry_price
         FROM paper_trades ORDER BY id DESC LIMIT ?1",
    )?;
    let rows = stmt.query_map(params![limit], |r| {
        Ok(PaperTrade {
            id: r.get(0)?,
            opened_at: r.get(1)?,
            symbol: r.get(2)?,
            side: r.get(3)?,
            quantity: r.get(4)?,
            entry_price: r.get(5)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

// Only tests read settings back right now; the app writes them.
#[cfg(test)]
pub fn get_setting(conn: &Connection, key: &str) -> Result<Option<String>, DbError> {
    let mut stmt = conn.prepare("SELECT value FROM settings WHERE key = ?1")?;
    let mut rows = stmt.query(params![key])?;
    Ok(match rows.next()? {
        Some(r) => Some(r.get(0)?),
        None => None,
    })
}

pub fn put_setting(conn: &Connection, key: &str, value: &str) -> Result<(), DbError> {
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?1, ?2)
         ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        params![key, value],
    )?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn db_path(dir: &tempfile::TempDir) -> PathBuf {
        dir.path().join("data").join("tradergo.db")
    }

    #[test]
    fn fresh_database_gets_latest_schema() {
        let dir = tempfile::tempdir().unwrap();
        let conn = open(&db_path(&dir)).unwrap();
        assert_eq!(schema_version(&conn).unwrap(), MIGRATIONS.len());
    }

    #[test]
    fn data_survives_reopen_like_an_app_update() {
        let dir = tempfile::tempdir().unwrap();
        let path = db_path(&dir);
        {
            let conn = open(&path).unwrap();
            insert_paper_trade(&conn, "BTCUSDT", "long", 0.1, 65000.0).unwrap();
            put_setting(&conn, "auto_download", "false").unwrap();
        }
        let conn = open(&path).unwrap();
        let trades = list_paper_trades(&conn, 10).unwrap();
        assert_eq!(trades.len(), 1);
        assert_eq!(trades[0].symbol, "BTCUSDT");
        assert_eq!(
            get_setting(&conn, "auto_download").unwrap().as_deref(),
            Some("false")
        );
    }

    #[test]
    fn upgrade_backs_up_and_keeps_data() {
        let dir = tempfile::tempdir().unwrap();
        let path = db_path(&dir);
        {
            let conn = open(&path).unwrap();
            insert_paper_trade(&conn, "ETHUSDT", "short", 1.0, 3000.0).unwrap();
        }
        let mut next: Vec<&str> = MIGRATIONS.to_vec();
        next.push("ALTER TABLE paper_trades ADD COLUMN note TEXT;");
        let conn = migrate(&path, &next).unwrap();
        assert_eq!(schema_version(&conn).unwrap(), next.len());
        assert_eq!(list_paper_trades(&conn, 10).unwrap().len(), 1);
        let backups = std::fs::read_dir(path.with_file_name("backups"))
            .unwrap()
            .count();
        assert_eq!(backups, 1);
    }

    #[test]
    fn failed_migration_rolls_back_completely() {
        let dir = tempfile::tempdir().unwrap();
        let path = db_path(&dir);
        {
            let conn = open(&path).unwrap();
            insert_paper_trade(&conn, "SOLUSDT", "long", 2.0, 150.0).unwrap();
        }
        let mut broken: Vec<&str> = MIGRATIONS.to_vec();
        broken.push("ALTER TABLE paper_trades ADD COLUMN ok TEXT; THIS IS NOT SQL;");
        assert!(migrate(&path, &broken).is_err());

        let conn = open(&path).unwrap();
        assert_eq!(schema_version(&conn).unwrap(), MIGRATIONS.len());
        assert_eq!(list_paper_trades(&conn, 10).unwrap().len(), 1);
        let cols: Vec<String> = conn
            .prepare("SELECT name FROM pragma_table_info('paper_trades')")
            .unwrap()
            .query_map([], |r| r.get(0))
            .unwrap()
            .collect::<Result<_, _>>()
            .unwrap();
        assert!(!cols.contains(&"ok".to_string()));
    }

    #[test]
    fn older_app_refuses_newer_database() {
        let dir = tempfile::tempdir().unwrap();
        let path = db_path(&dir);
        let mut next: Vec<&str> = MIGRATIONS.to_vec();
        next.push("CREATE TABLE future (id INTEGER);");
        drop(migrate(&path, &next).unwrap());
        assert!(matches!(open(&path), Err(DbError::NewerSchema { .. })));
    }

    #[test]
    fn non_paper_trades_are_rejected_by_schema() {
        let dir = tempfile::tempdir().unwrap();
        let conn = open(&db_path(&dir)).unwrap();
        let live = conn.execute(
            "INSERT INTO paper_trades (symbol, side, quantity, entry_price, mode)
             VALUES ('BTCUSDT', 'long', 1, 1, 'live')",
            [],
        );
        assert!(live.is_err());
    }
}
