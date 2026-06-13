"""The optional local dashboard: data shape + self-contained (loopback-only) HTML."""
from burndown.serve import _HTML, snapshot_data


def test_snapshot_data_shape(cfg):
    d = snapshot_data(cfg)
    assert {"spent", "budget", "by_project", "by_day",
            "programmatic", "interactive", "events", "tokens"} <= set(d)
    assert d["events"] >= 1
    assert isinstance(d["by_project"], list)


def test_dashboard_html_is_self_contained():
    # no external scripts/fonts/URLs — the page only ever talks to 127.0.0.1
    assert "https://" not in _HTML
    assert "http://" not in _HTML
    assert "/data.json" in _HTML        # fetches its own local endpoint
    assert "<script>" in _HTML          # inline JS, not a remote src
