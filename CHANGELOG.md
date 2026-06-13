# Changelog

## 0.1.0 — unreleased
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
