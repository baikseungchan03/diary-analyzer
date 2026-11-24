"""일기 테이블을 다룹니다."""

from ..crypto import decrypt_dict, encrypt_dict
from .connection import get_connection, lock


def load_entries(nickname):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM entries WHERE nickname = %s ORDER BY entry_date",
                (nickname,),
            )
            rows = cur.fetchall()
    return [decrypt_dict(payload) for (payload,) in rows]


def load_entry(nickname, date_str):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM entries WHERE nickname = %s AND entry_date = %s",
                (nickname, date_str),
            )
            row = cur.fetchone()
    return decrypt_dict(row[0]) if row else None


def save_entry(nickname, entry):
    payload = encrypt_dict(entry)
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO entries (nickname, entry_date, payload) VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE payload = VALUES(payload)
                """,
                (nickname, entry["date"], payload),
            )
        conn.commit()


def delete_entries(nickname):
    """한 사람의 일기를 전부 지웁니다. 지운 게 있으면 True."""
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM entries WHERE nickname = %s", (nickname,))
            changed = cur.rowcount > 0
        conn.commit()
    return changed