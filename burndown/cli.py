"""
burndown/cli.py — command-line entry. Subcommands:

  status   one-shot snapshot (default)
  watch    live terminal dashboard (re-reads logs every few seconds)
  budget   set/show the budget the forecast is measured against
  report   write a self-contained local HTML report
  check    exit non-zero if over / projected-over budget (for your own hooks)
  config   show config + verify which logs are being read
"""
from __future__ import annotations

import argparse
import sys
import time

from . import config as cfgmod
from . import report
from .aggregate import build_snapshot
from .forecast import build_forecast
from .logs import find_log_files, iter_events
from .money import KNOWN_FX, money


def _snapshot(cfg):
    snap = build_snapshot(iter_events(cfg.log_dirs), cfg)
    return snap, build_forecast(snap, cfg)


def cmd_status(cfg, args):
    snap, fc = _snapshot(cfg)
    print(report.render_status(snap, fc, cfg))


def cmd_watch(cfg, args):
    interval = max(2, getattr(args, "interval", 5))
    try:
        while True:
            cfg = cfgmod.load()
            snap, fc = _snapshot(cfg)
            sys.stdout.write("\033[2J\033[H")   # clear + home
            print(report.render_status(snap, fc, cfg))
            print(report.c(f"\n  refreshing every {interval}s · ctrl-c to quit", "gray"))
            time.sleep(interval)
    except KeyboardInterrupt:
        print()


def cmd_budget(cfg, args):
    if args.amount is None:
        val = "not set" if cfg.budget is None else money(cfg.budget, cfg)
        print(f"budget: {val} per {cfg.period} (resets day {cfg.reset_day})")
        return
    cfg.budget = float(args.amount)
    cfg.budget_unit = "tokens" if args.tokens else "usd"
    if args.period:
        cfg.period = args.period
    if args.reset_day:
        cfg.reset_day = max(1, min(28, args.reset_day))
    path = cfgmod.save(cfg)
    print(f"saved → {path}\n")
    cmd_status(cfgmod.load(), args)


def cmd_currency(cfg, args):
    if not args.code:
        sec = f"{cfg.currency2} @ {cfg.fx_rate}" if cfg.currency2 else "USD only"
        print(f"secondary currency: {sec}")
        print(f"known codes: {', '.join(KNOWN_FX)}")
        return
    code = args.code.upper()
    sym, default_rate = KNOWN_FX.get(code, (code + " ", 0.0))
    cfg.currency2 = code
    cfg.currency2_symbol = args.symbol or sym
    cfg.fx_rate = args.rate if args.rate else default_rate
    if not cfg.fx_rate:
        print(f"unknown code {code} — pass a rate: `burndown currency {code} --rate <USD->{code}>`")
        return
    path = cfgmod.save(cfg)
    print(f"saved → {path}  (showing USD + {code} @ {cfg.fx_rate}; static rate, no live fetch)\n")
    cmd_status(cfgmod.load(), args)


def cmd_config(cfg, args):
    files = find_log_files(cfg.log_dirs)
    pricing = "custom (config)" if cfg.pricing else "defaults — estimated, override in config"
    print(f"config file : {cfgmod.config_path()}")
    print(f"log dirs    : {', '.join(cfg.log_dirs)}")
    print(f"log files   : {len(files)} *.jsonl found")
    print(f"budget      : {cfg.budget if cfg.budget is not None else 'not set'} {cfg.budget_unit}")
    print(f"period      : {cfg.period} (reset day {cfg.reset_day})")
    print(f"pricing     : {pricing}")
    print("network     : none — burndown never opens a connection")


def cmd_report(cfg, args):
    snap, fc = _snapshot(cfg)
    out = args.html or "burndown-report.html"
    with open(out, "w") as f:
        f.write(report.render_html(snap, fc, cfg))
    print(f"wrote {out}")


def cmd_check(cfg, args):
    snap, fc = _snapshot(cfg)
    if fc.budget is None:
        print("no budget set — nothing to check")
        sys.exit(0)
    if fc.spent >= fc.budget:
        print(f"OVER budget: {money(fc.spent, cfg)} of {money(fc.budget, cfg)}")
        sys.exit(2)
    if fc.will_exceed:
        print(f"projected to exceed before reset ({money(fc.projected_period_total, cfg)})")
        sys.exit(1)
    print(f"within budget ({fc.pct_used:.0f}% used)")
    sys.exit(0)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="burndown",
        description="A local, real-time cockpit for your Claude credit burn. "
                    "Zero dependencies, 100%% local, nothing leaves your machine.")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("status", help="one-shot snapshot (default)")
    w = sub.add_parser("watch", help="live dashboard")
    w.add_argument("--interval", type=int, default=5)
    b = sub.add_parser("budget", help="set/show your budget")
    b.add_argument("amount", nargs="?", type=float)
    b.add_argument("--tokens", action="store_true", help="budget in tokens, not dollars")
    b.add_argument("--period", choices=["monthly", "weekly", "daily"])
    b.add_argument("--reset-day", dest="reset_day", type=int, help="day-of-month the pool resets")
    sub.add_parser("config", help="show config + which logs are read")
    cu = sub.add_parser("currency", help="show USD + a second currency (e.g. INR)")
    cu.add_argument("code", nargs="?", help="currency code, e.g. INR")
    cu.add_argument("--rate", type=float, help="USD -> code conversion (static, no live fetch)")
    cu.add_argument("--symbol", help="currency symbol, e.g. ₹")
    r = sub.add_parser("report", help="write a self-contained HTML report")
    r.add_argument("--html", help="output path (default burndown-report.html)")
    sub.add_parser("check", help="exit non-zero if over/projected-over budget")

    args = p.parse_args(argv)
    cfg = cfgmod.load()
    dispatch = {
        "status": cmd_status, "watch": cmd_watch, "budget": cmd_budget,
        "config": cmd_config, "currency": cmd_currency, "report": cmd_report,
        "check": cmd_check,
    }
    dispatch[args.cmd or "status"](cfg, args)
