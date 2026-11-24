"""계정 테이블을 다룹니다."""

from .connection import get_connection, lock


def get_account(nickname):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT salt, pin_hash, fails, locked_until, consent_version, consent_at "
                "FROM accounts WHERE nickname = %s",
                (nickname,),
            )
            row = cur.fetchone()
    if not row:
        return None
    salt, pin_hash, fails, locked_until, consent_version, consent_at = row
    return {
        "salt": salt,
        "hash": pin_hash,
        "fails": fails,
        "locked_until": locked_until,
        "consent": {"version": consent_version, "at": consent_at} if consent_version else {},
    }


def create_account(nickname, salt, pin_hash):
    """새 계정을 만듭니다. 이미 있으면 False."""
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM accounts WHERE nickname = %s", (nickname,))
            if cur.fetchone():
                return False
            cur.execute(
                "INSERT INTO accounts (nickname, salt, pin_hash) VALUES (%s, %s, %s)",
                (nickname, salt, pin_hash),
            )
        conn.commit()
    return True


def update_account(nickname, fails=None, locked_until=None, consent_version=None, consent_at=None):
    """계정의 일부 값만 바꿉니다. 인자로 안 넘긴 값은 그대로 둬요."""
    sets, params = [], []
    if fails is not None:
        sets.append("fails = %s")
        params.append(fails)
    if locked_until is not None:
        sets.append("locked_until = %s")
        params.append(locked_until)
    if consent_version is not None:
        sets.append("consent_version = %s")
        params.append(consent_version)
    if consent_at is not None:
        sets.append("consent_at = %s")
        params.append(consent_at)
    if not sets:
        return
    params.append(nickname)
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(f"UPDATE accounts SET {', '.join(sets)} WHERE nickname = %s", params)
        conn.commit()


def delete_account(nickname):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM accounts WHERE nickname = %s", (nickname,))
        conn.commit()