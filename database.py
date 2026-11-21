import sqlite3
from pathlib import Path
from typing import List, Tuple


DATABASE_PATH = Path(__file__).resolve().parent / "procurement.db"


def init_database() -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS procurement_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier TEXT NOT NULL,
                total_amount REAL NOT NULL,
                decision_summary TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def insert_record(
    supplier: str,
    total_amount: float,
    decision_summary: str,
) -> int:
    init_database()
    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO procurement_records
                (supplier, total_amount, decision_summary)
            VALUES (?, ?, ?)
            """,
            (supplier, float(total_amount), decision_summary),
        )
        return int(cursor.lastrowid)


def get_records() -> List[Tuple]:
    init_database()
    with sqlite3.connect(DATABASE_PATH) as connection:
        rows = connection.execute(
            """
            SELECT id, supplier, total_amount, decision_summary, created_at
            FROM procurement_records
            ORDER BY id DESC
            """
        ).fetchall()
    return rows
