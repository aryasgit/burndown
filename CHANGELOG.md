# Changelog

## 0.1.1 — unreleased
- **Web dashboard redesign** (`burndown serve`): now wears the same dark, editorial
  palette as the landing page — one green accent, hairline cards, a live pulse,
  monospace data with tight display numerals. Still fully self-contained (no external
  fonts or scripts) and 127.0.0.1-only.
- **Quieter terminal:** `budget`, `scope`, and `currency` print a one-line
  confirmation instead of re-dumping the whole status readout (run `burndown` to see
  it). Chaining set-commands no longer floods the screen.
- Clearer empty-project label: the no-`cwd` bucket reads `(no project)` instead of `—`.
- **Python 3.10 support:** dropped the floor from 3.11 to 3.10 via a tiny zero-dep
  TOML fallback (3.10 has no stdlib `tomllib`), so `pip install burndown` works for
  the large 3.10 cohort instead of erroring with "no matching distribution". CI now
  spans Python 3.10–3.13 across macOS / Linux / Windows.

## 0.1.0
Initial vertical slice.
- Read Claude Code usage logs (`~/.claude/projects/**/*.jsonl`), privacy-safe and
  read-only; de-dup by message uuid; skip `<synthetic>`.
- Configurable per-model pricing (estimated defaults) + token-budget mode.
- Period aggregation (monthly/weekly/daily) with by-project / by-model / by-day
  breakdowns and a 24h/7d recent-pace.
- Forecast: burn rate, runway (days-to-zero at recent pace), projected period
  total, over-budget detection.
- CLI: `status` · `watch` · `budget` · `check` · `report` (HTML) · `config` · `currency`.
- Dual-currency display (USD + a configurable secondary currency, e.g. INR) via a
  static FX rate — no live fetch, zero-network preserved (ADR-007).
- **Credit-pool guardian:** programmatic vs interactive split via the `entrypoint`
  field; `scope` config + `burndown scope programmatic` make the headline + runway
  meter just the June-2026 credit pool (ADR-009). Split always shown for context.
- **Local web dashboard:** `burndown serve` → auto-refreshing page on 127.0.0.1
  (loopback only, self-contained, no external resources; ADR-010).
- **Cross-platform:** macOS/Linux/Windows log-dir auto-discovery, `%APPDATA%`
  config on Windows, Windows ANSI enable, `\`-safe project names; CI matrix across
  all three OSes × Python 3.11–3.13 (ADR-011).
- Test suite: 23 tests across parser/pricing/aggregate/forecast/currency/scope/
  dashboard, incl. a structural content-blindness assertion. Zero runtime deps.
- Full decision log (8 ADRs) + threat model.
