from datetime import datetime, timedelta, timezone

from burndown.aggregate import build_snapshot, period_window
from burndown.config import Config
from burndown.logs import Event


def _ev(ts, model="opus", inp=1_000_000, out=0, proj="p", entrypoint="claude-desktop"):
    return Event(ts=ts, session_id="s", model=model, input=inp, output=out,
                 cache_write=0, cache_read=0, project=proj, branch="",
                 entrypoint=entrypoint, uuid=f"{ts}{model}{proj}{entrypoint}")


def test_period_window_monthly_default():
    now = datetime(2026, 6, 13, tzinfo=timezone.utc)
    s, e = period_window("monthly", 1, now)
    assert s == datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert e == datetime(2026, 7, 1, tzinfo=timezone.utc)


def test_period_window_reset_day_before():
    now = datetime(2026, 6, 13, tzinfo=timezone.utc)   # before reset day 15
    s, e = period_window("monthly", 15, now)
    assert s == datetime(2026, 5, 15, tzinfo=timezone.utc)
    assert e == datetime(2026, 6, 15, tzinfo=timezone.utc)


def test_period_window_year_rollover():
    now = datetime(2026, 12, 20, tzinfo=timezone.utc)
    s, e = period_window("monthly", 1, now)
    assert (s.year, s.month) == (2026, 12)
    assert (e.year, e.month) == (2027, 1)


def test_snapshot_rollup_and_recent_window():
    now = datetime(2026, 6, 13, 12, tzinfo=timezone.utc)
    cfg = Config(pricing={"opus": [15, 75, 18.75, 1.5]})
    evs = [_ev(now - timedelta(hours=2), proj="a"),
           _ev(now - timedelta(days=2), proj="b")]
    snap = build_snapshot(evs, cfg, now=now)
    assert snap.events == 2
    assert round(snap.spent_usd, 2) == 30.0          # 2 × $15 (1M input each)
    assert snap.cost_last_24h == 15.0                # only the 2h-ago event
    assert snap.cost_last_7d == 30.0
    assert set(snap.by_project) == {"a", "b"}


def test_scope_split_and_filter():
    now = datetime(2026, 6, 13, 12, tzinfo=timezone.utc)
    cfg = Config(pricing={"opus": [15, 75, 18.75, 1.5]})
    evs = [_ev(now - timedelta(hours=1), proj="a", entrypoint="claude-desktop"),
           _ev(now - timedelta(hours=1), proj="b", entrypoint="sdk-cli")]
    s_all = build_snapshot(evs, cfg, now=now, scope="all")
    assert round(s_all.spent_usd, 2) == 30.0
    assert round(s_all.spent_programmatic, 2) == 15.0     # the sdk-cli one
    assert round(s_all.spent_interactive, 2) == 15.0      # the claude-desktop one
    # guardian mode: headline + runway are about the credit pool only
    s_prog = build_snapshot(evs, cfg, now=now, scope="programmatic")
    assert round(s_prog.spent_usd, 2) == 15.0
    assert round(s_prog.cost_last_24h, 2) == 15.0
    assert set(s_prog.by_project) == {"b"}
