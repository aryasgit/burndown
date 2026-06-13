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
- Test suite: 19 tests across parser/pricing/aggregate/forecast/currency, incl. a
  structural content-blindness assertion. Zero runtime dependencies.
- Full decision log (8 ADRs) + threat model.
