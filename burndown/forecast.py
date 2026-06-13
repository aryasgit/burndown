"""
burndown/forecast.py — burn rate → runway. Pure, unit-tested.

Runway uses your RECENT pace (last 24h of spend) rather than the period average,
so it answers the real question: "at the rate I'm going *right now*, when do I
run out?" — not "what's my lazy lifetime average."
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .aggregate import Snapshot


@dataclass
class Forecast:
    burn_per_day: float          # recent pace (budget-unit / day) — basis for runway
    avg_per_day: float           # period-average pace
    elapsed_days: float
    remaining_days: float
    budget: float | None
    budget_unit: str
    spent: float                 # in budget units
    pct_used: float | None
    projected_period_total: float
    will_exceed: bool | None
    runway_days: float | None    # days until budget hit at the recent pace
    exhaustion_date: datetime | None


def _days(seconds: float) -> float:
    return seconds / 86400.0


def build_forecast(snap: Snapshot, cfg) -> Forecast:
    elapsed = max(_days((snap.now - snap.period_start).total_seconds()), 1e-9)
    remaining = max(_days((snap.period_end - snap.now).total_seconds()), 0.0)

    if cfg.budget_unit == "tokens":
        spent = float(snap.tokens)
        avg = spent / elapsed
        burn = avg                      # token-mode pace = period average (v0.1)
    else:
        spent = snap.spent_usd
        avg = spent / elapsed
        burn = snap.cost_last_24h if snap.cost_last_24h > 0 else avg

    budget = cfg.budget
    pct = (spent / budget * 100.0) if budget else None
    projected = spent + burn * remaining
    will_exceed = (projected > budget) if budget else None

    runway = exhaust = None
    if budget is not None and burn > 0:
        remaining_budget = budget - spent
        if remaining_budget <= 0:
            runway, exhaust = 0.0, snap.now
        else:
            runway = remaining_budget / burn
            exhaust = snap.now + timedelta(days=runway)

    return Forecast(
        burn_per_day=burn, avg_per_day=avg, elapsed_days=elapsed,
        remaining_days=remaining, budget=budget, budget_unit=cfg.budget_unit,
        spent=spent, pct_used=pct, projected_period_total=projected,
        will_exceed=will_exceed, runway_days=runway, exhaustion_date=exhaust,
    )
