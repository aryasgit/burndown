"""
burndown/report.py — terminal + HTML rendering. No external resources: the HTML
report is fully self-contained and opens from file:// with no network.
"""
from __future__ import annotations

import html
import os
import sys
from datetime import date, timedelta

from .aggregate import Snapshot
from .forecast import Forecast

_ANSI = {
    "reset": "\033[0m", "dim": "\033[2m", "b": "\033[1m",
    "red": "\033[31m", "grn": "\033[32m", "yel": "\033[33m",
    "cyan": "\033[36m", "gray": "\033[90m",
}


def _color_on() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def c(s, col: str) -> str:
    return f"{_ANSI[col]}{s}{_ANSI['reset']}" if _color_on() else str(s)


def _usd(x: float) -> str:
    return f"${x:,.2f}"


def _money(x: float, unit: str) -> str:
    return _usd(x) if unit == "usd" else f"{int(x):,} tok"


def _bar(frac: float, width: int = 28) -> str:
    frac = max(0.0, frac)
    filled = int(min(frac, 1.0) * width)
    body = "█" * filled + "░" * (width - filled)
    col = "red" if frac >= 1.0 else ("yel" if frac >= 0.8 else "grn")
    return c(body, col) + (c("  !!", "red") if frac > 1.0 else "")


def _spark(by_day: dict, days: int = 14) -> str:
    blocks = "▁▂▃▄▅▆▇█"
    today = date.today()
    series = [by_day.get((today - timedelta(days=days - 1 - i)).isoformat(), 0.0)
              for i in range(days)]
    mx = max(series) or 1.0
    return "".join(blocks[min(7, int(v / mx * 7))] for v in series)


def render_status(snap: Snapshot, fc: Forecast, cfg) -> str:
    L: list[str] = []
    L.append("  " + c("BURNDOWN", "b") +
             c(f"   {snap.period} period · resets {snap.period_end:%b %d}", "gray"))
    L.append("")

    spent_disp = _money(fc.spent, cfg.budget_unit)
    if fc.budget:
        frac = fc.spent / fc.budget
        L.append(f"  {spent_disp} / {_money(fc.budget, cfg.budget_unit)}   "
                 f"{_bar(frac)}  {c(f'{fc.pct_used:.0f}%', 'b')}")
    else:
        L.append(f"  {c(spent_disp, 'b')} spent this period   "
                 + c("(set a budget: `burndown budget <amount>`)", "yel"))
    L.append("")

    pace_unit = "/day" if cfg.budget_unit == "usd" else " tok/day"
    burn_disp = _usd(fc.burn_per_day) + "/day" if cfg.budget_unit == "usd" \
        else f"{int(fc.burn_per_day):,} tok/day"
    L.append(f"  burn rate   {c(burn_disp, 'cyan')}   {c('(last 24h)', 'gray')}"
             f"      avg {_money(fc.avg_per_day, cfg.budget_unit)}{pace_unit}")

    if fc.budget and fc.runway_days is not None:
        if fc.runway_days <= 0:
            L.append("  runway      " + c("budget exhausted", "red"))
        else:
            within = fc.runway_days < fc.remaining_days
            tail = c("← before reset!", "red") if within else c("✓ lasts the period", "grn")
            txt = f"{fc.runway_days:.1f} days  ({fc.exhaustion_date:%b %d})"
            L.append("  runway      " + c(txt, "red" if within else "grn") + "   " + tail)
        proj = _money(fc.projected_period_total, cfg.budget_unit)
        L.append(f"  projected   {proj} by reset"
                 + ("   " + c("OVER BUDGET", "red") if fc.will_exceed else ""))
    L.append("")

    if snap.by_project:
        L.append(c("  top projects", "gray"))
        for name, amt in sorted(snap.by_project.items(), key=lambda x: -x[1])[:4]:
            L.append(f"    {name[:26]:<26} {_usd(amt)}")
    if snap.by_day:
        L.append("")
        L.append("  last 14d    " + c(_spark(snap.by_day), "cyan"))
    L.append("")
    L.append(c(f"  {snap.events:,} billable msgs · {snap.tokens:,} tokens · "
               f"100% local, nothing sent anywhere", "gray"))
    return "\n".join(L)


def render_html(snap: Snapshot, fc: Forecast, cfg) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(k[:40])}</td><td class=n>{_usd(v)}</td></tr>"
        for k, v in sorted(snap.by_project.items(), key=lambda x: -x[1])[:10])
    budget_line = (
        f"{_money(fc.spent, cfg.budget_unit)} / {_money(fc.budget, cfg.budget_unit)} "
        f"({fc.pct_used:.0f}%)" if fc.budget else f"{_money(fc.spent, cfg.budget_unit)} (no budget set)")
    runway = ("—" if not fc.budget or fc.runway_days is None
              else ("exhausted" if fc.runway_days <= 0
                    else f"{fc.runway_days:.1f} days ({fc.exhaustion_date:%b %d})"))
    return f"""<!doctype html><html><head><meta charset=utf-8>
<title>Burndown report</title><style>
:root{{color-scheme:dark}}
body{{background:#0b0d10;color:#e6e6e6;font:15px/1.5 -apple-system,Segoe UI,sans-serif;max-width:720px;margin:40px auto;padding:0 20px}}
h1{{font-size:22px;margin:0 0 4px}}.sub{{color:#8a8a8a;font-size:13px;margin-bottom:24px}}
.card{{background:#14171c;border:1px solid #232830;border-radius:10px;padding:18px 20px;margin:14px 0}}
.big{{font-size:28px;font-weight:700}}.k{{color:#8a8a8a;font-size:13px}}
table{{width:100%;border-collapse:collapse;margin-top:6px}}td{{padding:6px 0;border-bottom:1px solid #1c2128}}
.n{{text-align:right;color:#7fd1a8}}.foot{{color:#5a5a5a;font-size:12px;margin-top:24px}}
</style></head><body>
<h1>Burndown</h1>
<div class=sub>{snap.period} period · resets {snap.period_end:%b %d} · generated locally</div>
<div class=card><div class=k>spent this period</div><div class=big>{html.escape(budget_line)}</div></div>
<div class=card><div class=k>burn rate (last 24h)</div><div class=big>{_usd(fc.burn_per_day)}/day</div>
<div class=k style="margin-top:10px">runway</div><div class=big>{html.escape(runway)}</div>
<div class=k style="margin-top:10px">projected by reset</div><div class=big>{_money(fc.projected_period_total, cfg.budget_unit)}</div></div>
<div class=card><div class=k>top projects</div><table>{rows or '<tr><td>—</td></tr>'}</table></div>
<div class=foot>{snap.events:,} billable messages · {snap.tokens:,} tokens · 100% local — this file was generated on your machine and contains no conversation content.</div>
</body></html>"""
