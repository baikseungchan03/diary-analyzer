"""하루 AI 사용 횟수를 세고 제한합니다."""

from datetime import datetime, timedelta, timezone

from . import db
from .config import (
    DAILY_LIMITS,
    GLOBAL_DAILY_LIMITS,
    KIND_LABELS,
    MAX_REFUNDS_PER_DAY,
)

KST = timezone(timedelta(hours=9))  # 한국 시간
KEEP_DAYS = 7                       # 최근 7일 기록만 남깁니다


def today_kst():
    """한국 시간 기준 오늘 날짜."""
    return datetime.now(KST).date()


def remaining(user, kind):
    """오늘 내가 쓸 수 있는 남은 횟수."""
    today = today_kst()
    mine = db.get_usage(today, user, kind)["count"]
    total = db.get_usage_total(today, kind)
    return max(0, min(DAILY_LIMITS[kind] - mine, GLOBAL_DAILY_LIMITS[kind] - total))


def try_use(user, kind):
    """횟수를 1 올립니다. (허용 여부, 안내 문구)를 돌려줘요."""
    today = today_kst()
    label = KIND_LABELS[kind]

    mine = db.get_usage(today, user, kind)["count"]
    if mine >= DAILY_LIMITS[kind]:
        return False, (
            f"오늘 {label} 횟수({DAILY_LIMITS[kind]}회)를 다 썼어요. 내일 다시 해보세요."
        )

    total = db.get_usage_total(today, kind)
    if total >= GLOBAL_DAILY_LIMITS[kind]:
        return False, (
            f"오늘은 모두가 쓸 수 있는 {label} 횟수가 다 찼어요. 내일 다시 해보세요."
        )

    db.increment_usage(today, user, kind)
    db.prune_usage(today - timedelta(days=KEEP_DAYS))
    return True, None


def refund(user, kind):
    """분석이 실패했을 때 횟수를 돌려줍니다. 돌려줬으면 True."""
    return db.refund_usage(today_kst(), user, kind, MAX_REFUNDS_PER_DAY)