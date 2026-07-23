import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_name TEXT,
            stocks TEXT,
            trigger_prices TEXT,
            triggered_at TEXT,
            received_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',       -- active | inactive
            last_state TEXT DEFAULT 'neutral',  -- neutral | bearish | bullish
            last_vwma REAL,
            last_close REAL,
            last_checked_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_report(scan_name, stocks, trigger_prices, triggered_at):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO reports (scan_name, stocks, trigger_prices, triggered_at) VALUES (?, ?, ?, ?)",
        (scan_name, stocks, trigger_prices, triggered_at),
    )
    conn.commit()
    conn.close()

def get_all_reports(limit=50):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM reports ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_to_watchlist(symbol):
    conn = sqlite3.connect(DB_PATH)
    # avoid duplicate active entries for the same symbol on the same day
    existing = conn.execute(
        "SELECT id FROM watchlist WHERE symbol=? AND status='active'", (symbol,)
    ).fetchone()
    if not existing:
        conn.execute("INSERT INTO watchlist (symbol) VALUES (?)", (symbol,))
        conn.commit()
    conn.close()

def get_active_watchlist():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM watchlist WHERE status='active'").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_watchlist_state(symbol, state, vwma, close):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """UPDATE watchlist SET last_state=?, last_vwma=?, last_close=?,
           last_checked_at=CURRENT_TIMESTAMP
           WHERE symbol=? AND status='active'""",
        (state, vwma, close, symbol),
    )
    conn.commit()
    conn.close()

def deactivate_all_watchlist():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE watchlist SET status='inactive' WHERE status='active'")
    conn.commit()
    conn.close()


