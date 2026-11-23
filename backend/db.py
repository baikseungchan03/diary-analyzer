"""MySQL에 일기, 계정, 사용량을 저장합니다."""

import os
import threading

import pymysql
from dotenv import load_dotenv

from .crypto import decrypt_dict, encrypt_dict

load_dotenv()

# 여러 사람이 동시에 읽고 써도 꼬이지 않게 한 번에 하나씩 처리해요
_lock = threading.Lock()
_conn = None  # 연결을 끊지 않고 계속 재사용해요 (속도 개선)


def _connect():
    """연결이 살아있으면 그대로 쓰고, 끊겼으면 새로 만듭니다."""
    global _conn
    if _conn is None or not _conn.open:
        _conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DB"),
            charset="utf8mb4",
            autocommit=False,
        )
    else:
        try:
            _conn.ping(reconnect=True)  # 연결이 살아있는지 확인, 끊겼으면 되살림
        except pymysql.err.Error:
            _conn = pymysql.connect(
                host=os.getenv("MYSQL_HOST", "localhost"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                user=os.getenv("MYSQL_USER"),
                password=os.getenv("MYSQL_PASSWORD"),
                database=os.getenv("MYSQL_DB"),
                charset="utf8mb4",
                autocommit=False,
            )
    return _conn


def init_db():
    """테이블이 없으면 만듭니다. 앱 시작 때 한 번 불러요."""
    with _lock:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    nickname VARCHAR(50) NOT NULL,
                    entry_date DATE NOT NULL,
                    payload LONGBLOB NOT NULL,
                    PRIMARY KEY (nickname, entry_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    nickname VARCHAR(50) PRIMARY KEY,
                    salt VARCHAR(64) NOT NULL,
                    pin_hash VARCHAR(64) NOT NULL,
                    fails INT NOT NULL DEFAULT 0,
                    locked_until DOUBLE NOT NULL DEFAULT 0,
                    consent_version INT NOT NULL DEFAULT 0,
                    consent_at VARCHAR(40) NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_daily (
                    usage_date DATE NOT NULL,
                    nickname VARCHAR(50) NOT NULL,
                    kind VARCHAR(20) NOT NULL,
                    count INT NOT NULL DEFAULT 0,
                    refunds INT NOT NULL DEFAULT 0,
                    PRIMARY KEY (usage_date, nickname, kind)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()


# ---------- 일기 ----------
def load_entries(nickname):
    with _lock:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM entries WHERE nickname = %s ORDER BY entry_date",
                (nickname,),
            )
            rows = cur.fetchall()
    return [decrypt_dict(payload) for (payload,) in rows]


def load_entry(nickname, date_str):
    with _lock:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM entries WHERE nickname = %s AND entry_date = %s",
                (nickname, date_str),
            )
            row = cur.fetchone()
    return decrypt_dict(row[0]) if row else None


def save_entry(nickname, entry):
    payload = encrypt_dict(entry)
    with _lock:
        conn = _connect()
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
    with _lock:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM entries WHERE nickname = %s", (nickname,))
            changed = cur.rowcount > 0
        conn.commit()
    return changed


# ---------- 계정 ----------
def get_account(nickname):
    with _lock:
        conn = _connect()
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
    with _lock:
        conn = _connect()
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
    with _lock:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(f"UPDATE accounts SET {', '.join(sets)} WHERE nickname = %s", params)
        conn.commit()


def delete_account(nickname):
    with _lock:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM accounts WHERE nickname = %s", (nickname,))
        conn.commit()


# ---------- 사용량 ----------
def get_usage(usage_date, nickname, kind):
    with _lock:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count, refunds FROM usage_daily "
                "WHERE usage_date = %s AND nickname = %s AND kind = %s",
                (usage_date, nickname, kind),
            )
            row = cur.fetchone()
    return {"count": row[0], "refunds": row[1]} if row else {"count": 0, "refunds": 0}


def get_usage_total(usage_date, kind):
    with _lock:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(count), 0) FROM usage_daily WHERE usage_date = %s AND kind = %s",
                (usage_date, kind),
            )
            (total,) = cur.fetchone()
    return total


def increment_usage(usage_date, nickname, kind):
    with _lock:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO usage_daily (usage_date, nickname, kind, count, refunds)
                VALUES (%s, %s, %s, 1, 0)
                ON DUPLICATE KEY UPDATE count = count + 1
                """,
                (usage_date, nickname, kind),
            )
        conn.commit()


def refund_usage(usage_date, nickname, kind, max_refunds):
    """성공하면 True. 돌려줄 횟수가 없거나 하루 환불 한도를 넘으면 False."""
    with _lock:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count, refunds FROM usage_daily "
                "WHERE usage_date = %s AND nickname = %s AND kind = %s FOR UPDATE",
                (usage_date, nickname, kind),
            )
            row = cur.fetchone()
            if not row or row[0] <= 0 or row[1] >= max_refunds:
                conn.rollback()
                return False
            cur.execute(
                "UPDATE usage_daily SET count = count - 1, refunds = refunds + 1 "
                "WHERE usage_date = %s AND nickname = %s AND kind = %s",
                (usage_date, nickname, kind),
            )
        conn.commit()
    return True


def prune_usage(keep_before):
    with _lock:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM usage_daily WHERE usage_date < %s", (keep_before,))
        conn.commit()