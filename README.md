<div align="center">

# Burndown

**A local, real-time cockpit for your Claude credit burn.**
Burn rate · runway forecast · budget alerts — so you see "I'll run dry in 3 days" *before* it happens, not after.

[![License: MIT](https://img.shields.io/badge/License-MIT-000.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-000.svg)](https://python.org)
[![Zero dependencies](https://img.shields.io/badge/dependencies-0-000.svg)]()
[![100%25 local](https://img.shields.io/badge/runs-100%25%20local-000.svg)]()

</div>

---

Anthropic split programmatic Claude usage into a **separate monthly credit pool**
that can run out mid-month. The existing tools show you what you *already* spent —
a bank statement, after the fact. Burndown is the **fuel gauge**: how fast you're
burning right now, when you'll hit zero, and a check that fires before you overspend.

It reads the usage logs Claude Code already writes on your machine. **Nothing
leaves your computer** — zero dependencies, no network, read-only on your logs,
and it never touches your prompts or code (see [SECURITY.md](docs/SECURITY.md)).

## Quickstart

```bash
pipx install burndown        # or: pip install burndown
burndown                     # snapshot of this period
burndown budget 100          # set your monthly credit-pool budget → get a runway
burndown scope programmatic  # guardian mode: meter just the credit pool
burndown currency INR        # show INR next to USD (static rate, no live fetch)
burndown watch               # live dashboard
```

No install? From a clone: `python -m burndown` (needs Python 3.11+, nothing else).

```
  BURNDOWN   monthly period · resets Jul 01

  $41.80 / $100.00   ███████████░░░░░░░░░░░░░░░░░  42%

  burn rate   $6.10/day   (last 24h)      avg $3.20/day
  runway      9.6 days  (Jun 22)   ✓ lasts the period
  projected   $89.40 by reset

  top projects
    memcon                     $22.10
    burndown                   $11.40
    barq-firmware              $8.30

  last 14d    ▂▁▃▅▂▇█▄▃▂▅▆▃▄

  1,204 billable msgs · 38,902,114 tokens · 100% local, nothing sent anywhere
```

## Commands

| Command | What it does |
|---|---|
| `burndown` / `burndown status` | one-shot snapshot |
| `burndown watch [--interval 5]` | live dashboard, re-reads logs every few seconds |
| `burndown budget <amount> [--tokens] [--reset-day N]` | set the budget runway is measured against (dollars, or `--tokens` to skip pricing) |
| `burndown scope programmatic` | **guardian mode** — meter just the June-2026 credit pool (programmatic usage); `all` / `interactive` also available |
| `burndown currency INR [--rate R]` | show a second currency next to USD (static rate, no live fetch) |
| `burndown check` | exit `0` ok · `1` projected-over · `2` over — wire it into your own pre-run hook / CI |
| `burndown report [--html out.html]` | self-contained local HTML report (opens from `file://`, no server) |
| `burndown config` | show config + verify which logs are being read |

## How it works

Claude Code logs every assistant message to `~/.claude/projects/**/*.jsonl` with
a `usage` block (input / output / cache-write / cache-read tokens). Burndown
reads those numbers (only those — never the message text), prices them with a
configurable per-model table, rolls them into your current billing period,
computes burn rate from the **last 24 hours**, and projects when you'll hit your
budget.

## Honest limitations

- **Pricing is estimated and configurable.** Default per-model rates are
  best-effort; correct them in `~/.config/burndown/config.toml` (`burndown
  config` shows the active table). The burn-rate/runway math is exact regardless
  — prices only scale the dollar figure. Prefer not to trust a dollar estimate?
  `burndown budget <N> --tokens` forecasts in raw tokens.
- It reads **local Claude Code logs**. If your usage doesn't write those logs
  (e.g. a flow that doesn't log locally), Burndown can't see it yet.
- The "budget stop" is a **check you act on**, not an auto-kill (on purpose — see
  [ADR-005](docs/DECISIONS.md)).

## Trust

Zero dependencies · no network · read-only · content-blind · MIT.
Verify it yourself in one line:
```bash
grep -REn "^[[:space:]]*(import|from)[[:space:]]+(socket|ssl|urllib|http|httpx|requests)" burndown/   # → nothing
```

Decisions are logged in [docs/DECISIONS.md](docs/DECISIONS.md); the threat model
is in [docs/SECURITY.md](docs/SECURITY.md).
