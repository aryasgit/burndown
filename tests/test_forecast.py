from datetime import datetime, timezone

from burndown.aggregate import Snapshot
from burndown.config import Config
from burndown.forecast import build_forecast

NOW = datetime(2026, 6, 13, tzinfo=timezone.utc)
START = datetime(2026, 6, 1, tzinfo=timezone.utc)
END = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _snap(spent, last24):
    s = Snapshot(now=NOW, period="monthly", period_start=START, period_end=END)
    s.spent_usd, s.cost_last_24h, s.events = spent, last24, 1
    return s


def test_runway_and_will_exceed():
    fc = build_forecast(_snap(40.0, 10.0), Config(budget=100.0))
    assert round(fc.runway_days, 1) == 6.0     # (100 - 40) / 10
    assert fc.will_exceed is True              # 40 + 10*18d remaining ≫ 100
    assert round(fc.pct_used) == 40


def test_no_budget_means_no_forecast():
    fc = build_forecast(_snap(40.0, 10.0), Config())
    assert fc.runway_days is None
    assert fc.will_exceed is None
    assert fc.pct_used is None


def test_exhausted_budget():
    fc = build_forecast(_snap(120.0, 10.0), Config(budget=100.0))
    assert fc.runway_days == 0.0


def test_recent_pace_drives_runway_not_average():
    # spent slowly all period, but burning hot in the last 24h → short runway
    fc = build_forecast(_snap(10.0, 30.0), Config(budget=100.0))
    assert round(fc.runway_days, 1) == 3.0     # (100-10)/30, not the lazy average
