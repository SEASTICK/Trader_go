-- Lokal marknadsdata för TraderGO. Filen ligger i appens datamapp, aldrig i Git eller appen.
-- Samma schema läses av motorn (engine/traderlab/data/live.py). Tider är millisekunder sedan 1970 i UTC.

-- Bara stängda, kontrollerade staplar. Det här är analysunderlaget.
CREATE TABLE IF NOT EXISTS bars (
    provider    TEXT    NOT NULL,
    market      TEXT    NOT NULL,
    symbol      TEXT    NOT NULL,
    interval    TEXT    NOT NULL,
    open_time   INTEGER NOT NULL,
    open        REAL    NOT NULL,
    high        REAL    NOT NULL,
    low         REAL    NOT NULL,
    close       REAL    NOT NULL,
    volume      REAL    NOT NULL,
    close_time  INTEGER NOT NULL,
    source      TEXT    NOT NULL,   -- rest | stream
    event_time  INTEGER,            -- serverns händelsetid (bara från strömmen)
    received_at INTEGER NOT NULL,   -- datorns mottagningstid
    PRIMARY KEY (provider, market, symbol, interval, open_time)
) WITHOUT ROWID;

-- Den pågående stapeln, en rad per serie. Aldrig analysunderlag.
CREATE TABLE IF NOT EXISTS live_bar (
    provider    TEXT    NOT NULL,
    market      TEXT    NOT NULL,
    symbol      TEXT    NOT NULL,
    interval    TEXT    NOT NULL,
    open_time   INTEGER NOT NULL,
    open        REAL    NOT NULL,
    high        REAL    NOT NULL,
    low         REAL    NOT NULL,
    close       REAL    NOT NULL,
    volume      REAL    NOT NULL,
    close_time  INTEGER NOT NULL,
    event_time  INTEGER,
    received_at INTEGER NOT NULL,
    PRIMARY KEY (provider, market, symbol, interval)
) WITHOUT ROWID;

-- En redan sparad stängd stapel som senare kom med andra värden. Originalet ändras aldrig.
CREATE TABLE IF NOT EXISTS corrections (
    id          INTEGER PRIMARY KEY,
    provider    TEXT    NOT NULL,
    market      TEXT    NOT NULL,
    symbol      TEXT    NOT NULL,
    interval    TEXT    NOT NULL,
    open_time   INTEGER NOT NULL,
    stored      TEXT    NOT NULL,   -- JSON
    incoming    TEXT    NOT NULL,   -- JSON
    source      TEXT    NOT NULL,
    detected_at INTEGER NOT NULL,
    UNIQUE (provider, market, symbol, interval, open_time, incoming)
);

-- Luckor som källan själv saknar (REST svarade utan staplar). Fylls aldrig med påhittade värden.
CREATE TABLE IF NOT EXISTS confirmed_gaps (
    provider     TEXT    NOT NULL,
    market       TEXT    NOT NULL,
    symbol       TEXT    NOT NULL,
    interval     TEXT    NOT NULL,
    from_open    INTEGER NOT NULL,
    to_open      INTEGER NOT NULL,
    confirmed_at INTEGER NOT NULL,
    PRIMARY KEY (provider, market, symbol, interval, from_open)
) WITHOUT ROWID;

-- Hämtningslogg: källa, serie, tid och kvalitet. Begränsas till de senaste raderna (se store.rs).
CREATE TABLE IF NOT EXISTS fetch_log (
    id       INTEGER PRIMARY KEY,
    at       INTEGER NOT NULL,
    provider TEXT    NOT NULL,
    market   TEXT    NOT NULL,
    symbol   TEXT    NOT NULL,
    interval TEXT    NOT NULL,
    kind     TEXT    NOT NULL,
    detail   TEXT    NOT NULL,
    quality  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
