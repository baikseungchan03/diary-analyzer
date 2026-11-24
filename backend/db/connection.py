"""MySQL 연결을 관리합니다. 연결을 끊지 않고 재사용해요."""

import os
import threading

import pymysql
from dotenv import load_dotenv

load_dotenv()

lock = threading.Lock()  # 여러 사람이 동시에 읽고 써도 꼬이지 않게 해요
_conn = None


def _make_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB"),
        charset="utf8mb4",
        autocommit=False,
    )


def get_connection():
    """연결이 살아있으면 그대로 쓰고, 끊겼으면 새로 만듭니다."""
    global _conn
    if _conn is None or not _conn.open:
        _conn = _make_connection()
    else:
        try:
            _conn.ping(reconnect=True)
        except pymysql.err.Error:
            _conn = _make_connection()
    return _conn