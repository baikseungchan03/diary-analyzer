"""테이블 구조를 정의하고 만듭니다."""

from .connection import get_connection, lock


def init_db():
    """테이블이 없으면 만듭니다. 앱 시작 때 한 번 불러요."""
    with lock:
        conn = get_connection()
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
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash VARCHAR(64) PRIMARY KEY,
                    nickname VARCHAR(50) NOT NULL,
                    expires_at DOUBLE NOT NULL,
                    rotate_after DOUBLE NOT NULL,
                    superseded_by VARCHAR(64) NULL
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
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token VARCHAR(64) PRIMARY KEY,
                    nickname VARCHAR(50) NOT NULL,
                    expires_at DOUBLE NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()