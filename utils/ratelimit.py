"""
Soft daily rate limiting per user, to protect the Gemini free tier from runaway usage.
"""
from datetime import datetime, timezone

import config
from database import db


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def check_and_bump_n(user_id: int, cost: int) -> tuple[bool, int]:
    """
    Reserves `cost` generations against today's quota in one atomic step.
    Returns (allowed, count_after). If the reservation would exceed the daily
    cap, nothing is bumped and (False, current_count) is returned — so a
    blocked multi-call batch (e.g. 'do all') never partially consumes quota.
    """
    day = _today()
    current = db.get_usage(user_id, day)
    if current + cost > config.DAILY_GENERATION_LIMIT:
        return False, current
    new_count = db.bump_usage_by(user_id, day, cost)
    return True, new_count


def check_and_bump(user_id: int) -> tuple[bool, int]:
    return check_and_bump_n(user_id, 1)
