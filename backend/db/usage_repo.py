"""하루 사용량 테이블을 다룹니다."""

from .connection import get_connection, lock


def get_usage(usage_date, nickname, kind):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count, refunds FROM usage_daily "
                "WHERE usage_date = %s AND nickname = %s AND kind = %s",
                (usage_date, nickname, kind),
            )
            row = cur.fetchone()
    return {"count": row[0], "refunds": row[1]} if row else {"count": 0, "refunds": 0}


def get_usage_total(usage_date, kind):
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(count), 0) FROM usage_daily WHERE usage_date = %s AND kind = %s",
                (usage_date, kind),
            )
            (total,) = cur.fetchone()
    return total


def increment_usage(usage_date, nickname, kind):
    with lock:
        conn = get_connection()
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
    with lock:
        conn = get_connection()
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
    with lock:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM usage_daily WHERE usage_date < %s", (keep_before,))
        conn.commit()