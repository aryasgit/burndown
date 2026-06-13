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
- CLI: `status` · `watch` · `budget` · `check` · `report` (HTML) · `config`.
- Zero runtime dependencies; full decision log + threat model.
