"""
burndown/config.py — local config at ~/.config/burndown/config.toml.

The config file is the ONLY thing burndown writes to disk (plus an HTML report
when you explicitly ask for one). It lives in your XDG config dir, is chmod 600,
and never leaves your machine.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:                                   # tomllib is in the stdlib on Python 3.11+
    import tomllib as _toml
    _TOML_ERROR = _toml.TOMLDecodeError

    def _loads(text: str) -> dict:
        return _toml.loads(text)
except ModuleNotFoundError:            # Python 3.10 and earlier — zero-dependency fallback
    _TOML_ERROR = ValueError

    def _loads(text: str) -> dict:
        return _loads_min(text)


def config_path() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "burndown" / "config.toml"


def default_log_dirs() -> list[str]:
    """Auto-discover Claude Code's log dir across macOS / Linux / Windows."""
    home = Path.home()
    cands = [home / ".claude" / "projects",
             home / ".config" / "claude" / "projects"]
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            cands.append(Path(appdata) / "Claude" / "projects")
    else:
        cands.append(home / "Library" / "Application Support" / "Claude" / "projects")
    found = [str(p) for p in cands if p.is_dir()]
    return found or [str(home / ".claude" / "projects")]


@dataclass
class Config:
    log_dirs: list[str] = field(default_factory=default_log_dirs)
    budget: float | None = None
    budget_unit: str = "usd"        # "usd" | "tokens"
    period: str = "monthly"         # "monthly" | "weekly" | "daily"
    reset_day: int = 1              # day-of-month the monthly pool resets (1..28)
    currency2: str = ""             # secondary display currency, e.g. "INR"
    currency2_symbol: str = ""      # e.g. "₹"
    fx_rate: float = 0.0            # USD -> currency2 (static; no live fetch — ADR-007)
    scope: str = "all"             # "all" | "programmatic" (credit pool) | "interactive"
    pricing: dict = field(default_factory=dict)   # per-model rate overrides


def _loads_min(text: str) -> dict:
    """Tiny TOML reader for burndown's OWN config format, so Python 3.10 (which has
    no stdlib `tomllib`) works with zero dependencies. Handles exactly what save()
    writes: top-level `key = value` (string / number / bool / array-of-strings)
    plus an optional `[pricing]` table of `key = array-of-floats`."""
    out: dict = {}
    section: dict = out
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line[0] == "[" and line[-1] == "]":
            section = out.setdefault(line[1:-1].strip(), {})
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        section[key.strip()] = _toml_value(val.strip())
    return out


def _toml_value(v: str):
    if v[:1] == "[" and v[-1:] == "]":
        body = v[1:-1].strip()
        return [_toml_scalar(x) for x in _toml_split(body)] if body else []
    return _toml_scalar(v)


def _toml_scalar(v: str):
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if v == "true":
        return True
    if v == "false":
        return False
    try:
        return float(v) if ("." in v or "e" in v.lower()) else int(v)
    except ValueError:
        return v


def _toml_split(body: str) -> list:
    """Split an array body on top-level commas (ignoring commas inside quotes)."""
    parts: list = []
    buf: list = []
    in_q = False
    for ch in body:
        if ch == '"':
            in_q = not in_q
        if ch == "," and not in_q:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def load() -> Config:
    cfg = Config()
    p = config_path()
    if not p.is_file():
        return cfg
    try:
        data = _loads(p.read_text())
    except (OSError, _TOML_ERROR):
        return cfg
    if isinstance(data.get("log_dirs"), list) and data["log_dirs"]:
        cfg.log_dirs = [str(x) for x in data["log_dirs"]]
    if isinstance(data.get("budget"), (int, float)):
        cfg.budget = float(data["budget"])
    if data.get("budget_unit") in ("usd", "tokens"):
        cfg.budget_unit = data["budget_unit"]
    if data.get("period") in ("monthly", "weekly", "daily"):
        cfg.period = data["period"]
    if isinstance(data.get("reset_day"), int):
        cfg.reset_day = max(1, min(28, data["reset_day"]))
    if isinstance(data.get("currency2"), str):
        cfg.currency2 = data["currency2"]
    if isinstance(data.get("currency2_symbol"), str):
        cfg.currency2_symbol = data["currency2_symbol"]
    if isinstance(data.get("fx_rate"), (int, float)):
        cfg.fx_rate = float(data["fx_rate"])
    if data.get("scope") in ("all", "programmatic", "interactive"):
        cfg.scope = data["scope"]
    if isinstance(data.get("pricing"), dict):
        cfg.pricing = data["pricing"]
    return cfg


def _toml_str(s: str) -> str:
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def save(cfg: Config) -> Path:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# burndown config — local only, never leaves your machine.",
        "log_dirs = [" + ", ".join(_toml_str(d) for d in cfg.log_dirs) + "]",
    ]
    if cfg.budget is not None:
        lines.append(f"budget = {cfg.budget!r}")
    lines.append(f"budget_unit = {_toml_str(cfg.budget_unit)}")
    lines.append(f"period = {_toml_str(cfg.period)}")
    lines.append(f"reset_day = {cfg.reset_day}")
    lines.append(f"scope = {_toml_str(cfg.scope)}")
    if cfg.currency2:
        lines.append(f"currency2 = {_toml_str(cfg.currency2)}")
        lines.append(f"currency2_symbol = {_toml_str(cfg.currency2_symbol)}")
        lines.append(f"fx_rate = {cfg.fx_rate!r}")
    if cfg.pricing:
        lines.append("")
        lines.append("[pricing]")
        for k, v in cfg.pricing.items():
            if isinstance(v, (list, tuple)):
                lines.append(f"{k} = [" + ", ".join(str(float(x)) for x in v) + "]")
    p.write_text("\n".join(lines) + "\n")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return p
