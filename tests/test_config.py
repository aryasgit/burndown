"""Config load/save + the zero-dep TOML fallback used on Python 3.10 (no tomllib)."""
from burndown.config import Config, config_path, load, save, _loads_min


def test_fallback_parses_our_format():
    # Exactly what save() writes: top-level scalars/arrays + a [pricing] table.
    text = (
        'log_dirs = ["/a/b", "C:\\\\Users\\\\k\\\\.claude"]\n'  # Windows path: doubled backslashes
        "budget = 100.0\n"
        'budget_unit = "usd"\n'
        'period = "monthly"\n'
        "reset_day = 7\n"
        'scope = "programmatic"\n'
        'currency2 = "INR"\n'
        'currency2_symbol = "₹"\n'
        "fx_rate = 83.0\n"
        "\n[pricing]\n"
        "opus = [15.0, 75.0, 18.75, 1.5]\n"
    )
    d = _loads_min(text)
    assert d["log_dirs"] == ["/a/b", "C:\\Users\\k\\.claude"]  # un-escaped back to one backslash
    assert d["budget"] == 100.0 and isinstance(d["budget"], float)
    assert d["reset_day"] == 7 and isinstance(d["reset_day"], int)
    assert d["scope"] == "programmatic"
    assert d["currency2"] == "INR"
    assert d["fx_rate"] == 83.0
    assert d["pricing"]["opus"] == [15.0, 75.0, 18.75, 1.5]


def test_fallback_ignores_comments_and_blanks():
    assert _loads_min("# just a comment\n\n   \nscope = \"all\"\n") == {"scope": "all"}


def test_save_load_roundtrip(tmp_path, monkeypatch):
    # Isolate the Windows config path too (XDG is already isolated by the autouse
    # fixture); exercises whichever parser is active on this interpreter.
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    cfg = Config(budget=250.0, reset_day=15, scope="programmatic",
                 currency2="INR", currency2_symbol="₹", fx_rate=83.0,
                 pricing={"opus": [15.0, 75.0, 18.75, 1.5]})
    save(cfg)
    got = load()
    assert got.budget == 250.0
    assert got.reset_day == 15
    assert got.scope == "programmatic"
    assert got.currency2 == "INR"
    assert got.fx_rate == 83.0
    assert got.pricing["opus"] == [15.0, 75.0, 18.75, 1.5]


def test_config_written_as_utf8(tmp_path, monkeypatch):
    # The config carries non-ASCII currency symbols (₹, €, £). It must be written
    # and read as UTF-8 on every OS — not the platform default (cp1252 on Windows,
    # which can't encode ₹ and used to crash `burndown currency INR` there).
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    save(Config(currency2="INR", currency2_symbol="₹", fx_rate=83.0))
    raw = config_path().read_bytes()
    assert "₹" in raw.decode("utf-8")          # round-trips as UTF-8
    assert b"\xe2\x82\xb9" in raw               # the literal UTF-8 bytes for ₹
