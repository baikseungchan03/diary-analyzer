"""일기를 SQLite 파일에 암호화해서 저장합니다."""

import os
import sqlite3
import threading

from .config import DB_FILE
from .crypto import decrypt_dict, encrypt_dict

# 여러 사람이 동시에 읽고 써도 꼬이지 않게 한 번에 하나씩 처리해요
_lock = threading.Lock()


def _connect():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            nickname TEXT NOT NULL,
            date TEXT NOT NULL,
            payload BLOB NOT NULL,
            PRIMARY KEY (nickname, date)
        )
        """
    )
    return conn


def load_entries(nickname):
    """한 사람의 모든 일기를 날짜순으로 읽어옵니다."""
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT payload FROM entries WHERE nickname = ? ORDER BY date",
                (nickname,),
            ).fetchall()
        finally:
            conn.close()
    return [decrypt_dict(payload) for (payload,) in rows]


def load_entry(nickname, date_str):
    """특정 날짜의 일기 하나를 읽어옵니다. 없으면 None."""
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT payload FROM entries WHERE nickname = ? AND date = ?",
                (nickname, date_str),
            ).fetchone()
        finally:
            conn.close()
    return decrypt_dict(row[0]) if row else None


def save_entry(nickname, entry):
    """일기 하나를 저장합니다. 같은 날짜면 덮어써요."""
    payload = encrypt_dict(entry)
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO entries (nickname, date, payload) VALUES (?, ?, ?)
                ON CONFLICT(nickname, date) DO UPDATE SET payload = excluded.payload
                """,
                (nickname, entry["date"], payload),
            )
            conn.commit()
        finally:
            conn.close()


def delete_user(nickname):
    """한 사람의 일기를 전부 지웁니다. 지운 게 있으면 True."""
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM entries WHERE nickname = ?", (nickname,))
            conn.commit()
            changed = cur.rowcount > 0
        finally:
            conn.close()
    return changed