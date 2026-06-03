import sqlite3
import os
import streamlit as st

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "canon_pro.db")


def get_conn():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS logbook (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            loc TEXT DEFAULT '',
            sub TEXT DEFAULT '',
            settings TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            rating TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            typ TEXT DEFAULT '',
            lat REAL DEFAULT 0,
            lon REAL DEFAULT 0,
            beste_zeit TEXT DEFAULT '',
            notizen TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def get_logbook(search=""):
    conn = get_conn()
    if search:
        rows = conn.execute(
            "SELECT * FROM logbook WHERE loc LIKE ? OR sub LIKE ? OR notes LIKE ? ORDER BY id DESC",
            (f"%{search}%", f"%{search}%", f"%{search}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM logbook ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def add_logbook_entry(date, loc, sub, settings, notes, rating):
    conn = get_conn()
    conn.execute(
        "INSERT INTO logbook (date, loc, sub, settings, notes, rating) VALUES (?, ?, ?, ?, ?, ?)",
        (date, loc, sub, settings, notes, rating),
    )
    conn.commit()
    conn.close()


def clear_logbook():
    conn = get_conn()
    conn.execute("DELETE FROM logbook")
    conn.commit()
    conn.close()


def get_spots():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM spots ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def add_spot(name, typ, lat, lon, beste_zeit, notizen):
    conn = get_conn()
    conn.execute(
        "INSERT INTO spots (name, typ, lat, lon, beste_zeit, notizen) VALUES (?, ?, ?, ?, ?, ?)",
        (name, typ, lat, lon, beste_zeit, notizen),
    )
    conn.commit()
    conn.close()


def clear_spots():
    conn = get_conn()
    conn.execute("DELETE FROM spots")
    conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_api_key(key_name):
    try:
        return st.secrets[key_name]
    except (KeyError, TypeError):
        db_val = get_setting(key_name)
        if db_val:
            return db_val
    return None


def track_usage(tool_name):
    conn = get_conn()
    key = f"usage:{tool_name}"
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    count = (int(row["value"]) if row else 0) + 1
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(count)))
    conn.commit()
    conn.close()


def get_top_tools(limit=12):
    conn = get_conn()
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key LIKE 'usage:%' ORDER BY CAST(value AS INTEGER) DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [(row["key"][6:], int(row["value"])) for row in rows]
