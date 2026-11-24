"""로그인 유지 토큰 테이블을 다룹니다."""

from .connection import get_connection, lock


def save_session(token, nickname, expires_at):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (token, nickname, expires_at) VALUES (%s, %s, %s)",
                (token, nickname, expires_at),
            )
        conn.commit()


def get_session(token):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT nickname, expires_at FROM sessions WHERE token = %s", (token,)
            )
            row = cur.fetchone()
    if not row:
        return None
    return {"nickname": row[0], "expires_at": row[1]}


def delete_session(token):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE token = %s", (token,))
        conn.commit()


def prune_sessions(now):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE expires_at < %s", (now,))
        conn.commit()