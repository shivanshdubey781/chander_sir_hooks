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

