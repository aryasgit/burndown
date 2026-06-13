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
from .money import dual, fmt_usd, money, rate

_ANSI = {
    "reset": "\033[0m", "dim": "\033[2m", "b": "\033[1m",
    "red": "\033[31m", "grn": "\033[32m", "yel": "\033[33m",
    "cyan": "\033[36m", "gray": "\033[90m",
}


def _color_on() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def c(s, col: str) -> str:
    return f"{_ANSI[col]}{s}{_ANSI['reset']}" if _color_on() else str(s)


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
    scope = getattr(cfg, "scope", "all")
    head = f"   {snap.period} period · resets {snap.period_end:%b %d}"
    if scope != "all":
        head += f" · scope: {scope}"
    L.append("  " + c("BURNDOWN", "b") + c(head, "gray"))
    L.append("")

    if fc.budget:
        frac = fc.spent / fc.budget
        L.append(f"  {money(fc.spent, cfg)} / {money(fc.budget, cfg)}   "
                 f"{_bar(frac)}  {c(f'{fc.pct_used:.0f}%', 'b')}")
    else:
        L.append(f"  {c(money(fc.spent, cfg), 'b')} spent this period   "
                 + c("(set a budget: `burndown budget <amount>`)", "yel"))
    L.append("")

    if snap.spent_programmatic or snap.spent_interactive:
        L.append("  " + c("programmatic", "cyan") + f" {dual(snap.spent_programmatic, cfg)}  "
                 + c("(credit pool)", "gray") + "     " + c("interactive", "gray")
                 + f" {dual(snap.spent_interactive, cfg)}")
        L.append("")
    L.append(f"  burn rate   {c(rate(fc.burn_per_day, cfg), 'cyan')}   {c('(last 24h)', 'gray')}"
             f"      avg {rate(fc.avg_per_day, cfg)}")

    if fc.budget and fc.runway_days is not None:
        if fc.runway_days <= 0:
            L.append("  runway      " + c("budget exhausted", "red"))
        else:
            within = fc.runway_days < fc.remaining_days
            tail = c("← before reset!", "red") if within else c("✓ lasts the period", "grn")
            txt = f"{fc.runway_days:.1f} days  ({fc.exhaustion_date:%b %d})"
            L.append("  runway      " + c(txt, "red" if within else "grn") + "   " + tail)
        L.append(f"  projected   {money(fc.projected_period_total, cfg)} by reset"
                 + ("   " + c("OVER BUDGET", "red") if fc.will_exceed else ""))
    L.append("")

    if snap.by_project:
        L.append(c("  top projects", "gray"))
        for name, amt in sorted(snap.by_project.items(), key=lambda x: -x[1])[:4]:
            L.append(f"    {name[:26]:<26} {dual(amt, cfg)}")
    if snap.by_day:
        L.append("")
        L.append("  last 14d    " + c(_spark(snap.by_day), "cyan"))
    L.append("")
    L.append(c(f"  {snap.events:,} billable msgs · {snap.tokens:,} tokens · "
               f"100% local, nothing sent anywhere", "gray"))
    return "\n".join(L)


def render_html(snap: Snapshot, fc: Forecast, cfg) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(k[:40])}</td><td class=n>{html.escape(dual(v, cfg))}</td></tr>"
        for k, v in sorted(snap.by_project.items(), key=lambda x: -x[1])[:10])
    budget_line = (
        f"{money(fc.spent, cfg)} / {money(fc.budget, cfg)} ({fc.pct_used:.0f}%)"
        if fc.budget else f"{money(fc.spent, cfg)} (no budget set)")
    runway = ("—" if not fc.budget or fc.runway_days is None
              else ("exhausted" if fc.runway_days <= 0
                    else f"{fc.runway_days:.1f} days ({fc.exhaustion_date:%b %d})"))
    return f"""<!doctype html><html><head><meta charset=utf-8>
<title>Burndown report</title><style>
:root{{color-scheme:dark}}
body{{background:#0b0d10;color:#e6e6e6;font:15px/1.5 -apple-system,Segoe UI,sans-serif;max-width:720px;margin:40px auto;padding:0 20px}}
h1{{font-size:22px;margin:0 0 4px}}.sub{{color:#8a8a8a;font-size:13px;margin-bottom:24px}}
.card{{background:#14171c;border:1px solid #232830;border-radius:10px;padding:18px 20px;margin:14px 0}}
.big{{font-size:26px;font-weight:700}}.k{{color:#8a8a8a;font-size:13px}}
table{{width:100%;border-collapse:collapse;margin-top:6px}}td{{padding:6px 0;border-bottom:1px solid #1c2128}}
.n{{text-align:right;color:#7fd1a8}}.foot{{color:#5a5a5a;font-size:12px;margin-top:24px}}
</style></head><body>
<h1>Burndown</h1>
<div class=sub>{snap.period} period · resets {snap.period_end:%b %d} · generated locally</div>
<div class=card><div class=k>spent this period</div><div class=big>{html.escape(budget_line)}</div></div>
<div class=card><div class=k>burn rate (last 24h)</div><div class=big>{html.escape(rate(fc.burn_per_day, cfg))}</div>
<div class=k style="margin-top:10px">runway</div><div class=big>{html.escape(runway)}</div>
<div class=k style="margin-top:10px">projected by reset</div><div class=big>{html.escape(money(fc.projected_period_total, cfg))}</div></div>
<div class=card><div class=k>top projects</div><table>{rows or '<tr><td>—</td></tr>'}</table></div>
<div class=foot>{snap.events:,} billable messages · {snap.tokens:,} tokens · 100% local — generated on your machine, contains no conversation content.</div>
</body></html>"""
