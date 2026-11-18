"""하루 AI 사용 횟수를 세고 제한합니다."""

import json
import os
import threading
from datetime import datetime, timedelta, timezone

from config import (
    DAILY_LIMITS,
    GLOBAL_DAILY_LIMITS,
    KIND_LABELS,
    MAX_REFUNDS_PER_DAY,
    USAGE_FILE,
)

KST = timezone(timedelta(hours=9))  # 한국 시간
KEEP_DAYS = 7                       # 최근 7일 기록만 남깁니다

# 여러 사람이 동시에 눌러도 횟수가 꼬이지 않게 한 번에 한 명씩 처리해요
_lock = threading.Lock()


def today_kst():
    """한국 시간 기준 오늘 날짜."""
    return datetime.now(KST).date()


def _today_key():
    return today_kst().isoformat()


def _load():
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(data):
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    tmp = USAGE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, USAGE_FILE)  # 쓰다가 끊겨도 파일이 깨지지 않게


def _prune(data):
    for day in sorted(data.keys())[:-KEEP_DAYS]:
        del data[day]


def remaining(user, kind):
    """오늘 내가 쓸 수 있는 남은 횟수."""
    with _lock:
        day = _load().get(_today_key(), {})
    mine = day.get("users", {}).get(user, {}).get(kind, 0)
    total = day.get("total", {}).get(kind, 0)
    return max(0, min(DAILY_LIMITS[kind] - mine, GLOBAL_DAILY_LIMITS[kind] - total))


def try_use(user, kind):
    """횟수를 1 올립니다. (허용 여부, 안내 문구)를 돌려줘요."""
    label = KIND_LABELS[kind]
    with _lock:
        data = _load()
        day = data.setdefault(_today_key(), {"total": {}, "users": {}})
        mine = day["users"].setdefault(user, {})

        if mine.get(kind, 0) >= DAILY_LIMITS[kind]:
            return False, (
                f"오늘 {label} 횟수({DAILY_LIMITS[kind]}회)를 다 썼어요. "
                "내일 다시 해보세요."
            )
        if day["total"].get(kind, 0) >= GLOBAL_DAILY_LIMITS[kind]:
            return False, (
                f"오늘은 모두가 쓸 수 있는 {label} 횟수가 다 찼어요. "
                "내일 다시 해보세요."
            )

        mine[kind] = mine.get(kind, 0) + 1
        day["total"][kind] = day["total"].get(kind, 0) + 1
        _prune(data)
        _save(data)
    return True, None


def refund(user, kind):
    """분석이 실패했을 때 횟수를 돌려줍니다. 돌려줬으면 True."""
    with _lock:
        data = _load()
        day = data.get(_today_key())
        if not day:
            return False
        mine = day.get("users", {}).get(user)
        if mine is None or mine.get(kind, 0) <= 0:
            return False
        if mine.get("_refunds", 0) >= MAX_REFUNDS_PER_DAY:
            return False  # 오늘 돌려줄 수 있는 횟수를 다 썼어요

        mine[kind] -= 1
        mine["_refunds"] = mine.get("_refunds", 0) + 1
        day["total"][kind] = max(0, day["total"].get(kind, 0) - 1)
        _save(data)
    return True