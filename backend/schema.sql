-- Trading journal schema. Images live in the same row as BLOB columns,
-- so a trade and its screenshots are always one atomic record.

CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,          -- YYYY-MM-DD
    time            TEXT,                   -- HH:MM
    asset           TEXT NOT NULL DEFAULT '',
    setup           TEXT NOT NULL DEFAULT '',
    confluences     TEXT NOT NULL DEFAULT '[]',  -- JSON-encoded array of strings
    entry           REAL NOT NULL,
    stop            REAL NOT NULL,
    exit            REAL NOT NULL,
    risk            REAL NOT NULL DEFAULT 0,
    session         TEXT NOT NULL DEFAULT '',
    thesis          TEXT NOT NULL DEFAULT '',
    filled          INTEGER NOT NULL DEFAULT 1 CHECK (filled IN (0, 1)),  -- 0 = order never filled; excluded from statistics
    shot_before     BLOB,                   -- raw image bytes
    shot_before_mime TEXT,
    shot_after      BLOB,
    shot_after_mime TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date);
CREATE INDEX IF NOT EXISTS idx_trades_asset ON trades(asset);
