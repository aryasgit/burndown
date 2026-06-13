"""
burndown/aggregate.py — roll a stream of Events into a period Snapshot.
Pure functions, no I/O — unit-tested offline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .pricing import cost_usd


def period_window(period: str, reset_day: int, now: datetime) -> tuple[datetime, datetime]:
    """[start, end) of the billing window `now` falls in."""
    now = now.astimezone(timezone.utc)
    if period == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)
    if period == "weekly":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(weeks=1)
    # monthly, anchored on reset_day
    rd = max(1, min(28, reset_day))
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if now.day >= rd:
        start = midnight.replace(day=rd)
    else:
        prev_last = midnight.replace(day=1) - timedelta(days=1)
        start = prev_last.replace(day=rd)
    end = start.replace(year=start.year + 1, month=1) if start.month == 12 \
        else start.replace(month=start.month + 1)
    return start, end


@dataclass
class Snapshot:
    now: datetime
    period: str
    period_start: datetime
    period_end: datetime
    spent_usd: float = 0.0
    tokens: int = 0
    events: int = 0
    by_project: dict = field(default_factory=dict)   # name -> usd
    by_model: dict = field(default_factory=dict)      # model -> usd
    by_day: dict = field(default_factory=dict)        # 'YYYY-MM-DD' -> usd
    cost_last_24h: float = 0.0
    cost_last_7d: float = 0.0


def build_snapshot(events, cfg, now: datetime | None = None) -> Snapshot:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start, end = period_window(cfg.period, cfg.reset_day, now)
    snap = Snapshot(now=now, period=cfg.period, period_start=start, period_end=end)
    t24, t7 = now - timedelta(hours=24), now - timedelta(days=7)
    for e in events:
        c = cost_usd(e.model, e.input, e.output, e.cache_write, e.cache_read, cfg.pricing)
        if t24 <= e.ts <= now:
            snap.cost_last_24h += c
        if t7 <= e.ts <= now:
            snap.cost_last_7d += c
        if not (start <= e.ts < end):
            continue
        snap.spent_usd += c
        snap.tokens += e.total_tokens
        snap.events += 1
        snap.by_project[e.project] = snap.by_project.get(e.project, 0.0) + c
        snap.by_model[e.model] = snap.by_model.get(e.model, 0.0) + c
        d = e.ts.date().isoformat()
        snap.by_day[d] = snap.by_day.get(d, 0.0) + c
    return snap
