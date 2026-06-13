"""
burndown/config.py — local config at ~/.config/burndown/config.toml.

The config file is the ONLY thing burndown writes to disk (plus an HTML report
when you explicitly ask for one). It lives in your XDG config dir, is chmod 600,
and never leaves your machine.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "burndown" / "config.toml"


def default_log_dirs() -> list[str]:
    p = Path.home() / ".claude" / "projects"
    return [str(p)]


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


def load() -> Config:
    cfg = Config()
    p = config_path()
    if not p.is_file():
        return cfg
    try:
        data = tomllib.loads(p.read_text())
    except (OSError, tomllib.TOMLDecodeError):
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
