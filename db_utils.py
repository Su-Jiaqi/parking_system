from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "parking.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS parking_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT NOT NULL,
                entry_time TEXT,
                exit_time TEXT,
                duration_minutes INTEGER,
                fee REAL,
                status TEXT NOT NULL,
                image_path TEXT
            )
            """
        )
        conn.commit()


def fetch_one(query: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute(query, tuple(params))
        return cur.fetchone()


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute(query, tuple(params))
        return cur.fetchall()


def execute(query: str, params: Iterable[Any] = ()) -> int:
    with get_connection() as conn:
        cur = conn.execute(query, tuple(params))
        conn.commit()
        return cur.lastrowid
