"""Parser: de-dup, skips, and the structural content-blindness guarantee."""
from burndown.logs import Event, iter_events


def test_parses_dedups_and_skips(log_dir):
    evs = list(iter_events([log_dir]))
    assert sorted(e.uuid for e in evs) == ["A", "B"]  # dup A merged; synthetic/user/no-usage/garbage skipped
    a = next(e for e in evs if e.uuid == "A")
    assert a.model == "claude-opus-4-8"
    assert a.input == 1000 and a.output == 2000
    assert a.project == "proj-a"          # derived from cwd basename
    assert a.branch == "main"
    assert a.ts.tzinfo is not None         # tz-aware


def test_content_blind_by_construction():
    # The Event carries ONLY usage + metadata. There is no field that could ever
    # hold message content — this is the privacy guarantee, enforced structurally.
    assert set(Event.__annotations__) == {
        "ts", "session_id", "model", "input", "output",
        "cache_write", "cache_read", "project", "branch", "uuid",
    }


def test_missing_dir_is_safe():
    assert list(iter_events(["/nonexistent/path/xyz"])) == []
