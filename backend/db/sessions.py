"""로그인 유지 토큰 테이블을 다룹니다."""

from .connection import get_connection, lock


def save_session(token_hash, nickname, expires_at, rotate_after):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (token_hash, nickname, expires_at, rotate_after, superseded_by)
                VALUES (%s, %s, %s, %s, NULL)
                """,
                (token_hash, nickname, expires_at, rotate_after),
            )
        conn.commit()


def get_session(token_hash):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT nickname, expires_at, rotate_after, superseded_by "
                "FROM sessions WHERE token_hash = %s",
                (token_hash,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "nickname": row[0],
        "expires_at": row[1],
        "rotate_after": row[2],
        "superseded_by": row[3],
    }


def mark_superseded(old_hash, new_hash):
    """옛 토큰을 지우지 않고, '이 토큰으로 교체됐다'는 표시만 남깁니다.
    재사용 탐지를 위해서예요."""
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET superseded_by = %s WHERE token_hash = %s",
                (new_hash, old_hash),
            )
        conn.commit()


def delete_session(token_hash):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))
        conn.commit()


def delete_sessions_for_user(nickname):
    """그 사람의 모든 세션을 강제로 지웁니다. (재사용 탐지 시 전체 로그아웃용)"""
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE nickname = %s", (nickname,))
        conn.commit()


def prune_sessions(now):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE expires_at < %s", (now,))
        conn.commit()