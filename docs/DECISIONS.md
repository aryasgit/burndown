# Decision log

Every non-obvious choice, with the reasoning, so the project can be audited and
so future-me (or a new contributor) doesn't re-litigate settled questions.
Newest at the bottom. Format: context → decision → why → status.

---

### ADR-001 — Zero runtime dependencies (pure Python stdlib)
**Context:** Burndown reads local files that sit next to sensitive data, for a
user whose #1 requirement is "no security leaks."
**Decision:** No runtime dependencies at all. JSON via `json`, config via
`tomllib`, terminal UI via raw ANSI, HTML via string templating — all stdlib.
Dev-only dependency: `pytest`.
**Why:** (1) the entire tool is auditable in a single sitting; (2) zero
supply-chain surface — there is no transitive package that could phone home or
get compromised; (3) trivial install (`pipx install`, or just run the folder).
This is a *security feature*, not an aesthetic one.
**Status:** holding. Requires Python ≥ 3.11 for stdlib `tomllib`.

### ADR-002 — Local-only, read-only, content-blind
**Context:** Claude Code session logs contain full conversation content (prompts,
code, responses) alongside the token-usage numbers we actually need.
**Decision:** The parser extracts ONLY usage integers + minimal metadata (model,
timestamp, session id, project folder *name*, git branch). It never reads,
stores, or transmits `message.content`. Files are opened read-only; the only
things Burndown writes are its own config (`~/.config/burndown/`) and an HTML
report you explicitly request.
**Why:** can't leak what you never read or send. The threat model is in
`SECURITY.md`.
**Status:** enforced in `logs.py`; to be covered by a test asserting no network
modules are imported.

### ADR-003 — Parser grounded on the real log schema, not assumptions
**Context:** Log formats drift; building on a guessed schema would silently
mis-count.
**Decision:** Inspected 133 real `~/.claude/projects/**/*.jsonl` files (structure
only, no content) before writing the parser. Confirmed: billable events are
`type:"assistant"` lines with `message.usage` →
`input_tokens / output_tokens / cache_creation_input_tokens /
cache_read_input_tokens`; de-dup key is the per-message `uuid`; skip the
`<synthetic>` model (no real cost); group by `cwd` / `gitBranch`.
**Why:** correctness from real data beats a plausible guess.
**Status:** done. If the schema changes, the parser degrades gracefully (skips
unrecognized lines) rather than crashing.

### ADR-004 — Pricing is estimated + user-configurable; token-budget mode exists
**Context:** Exact, current Anthropic per-model pricing is not something we can
pin reliably, and it changes.
**Decision:** Ship best-effort default rates (Opus/Sonnet/Haiku, per-MTok, 4
token types), clearly labeled estimates and overridable in config. Unknown
models fall back to the most-expensive tier so we never under-report. Also
support budgeting/forecasting in raw **tokens** so a user can ignore dollars
entirely.
**Why:** honesty. The burn-rate/runway math is exact regardless of the rates —
prices only scale the dollar figure — and token-mode sidesteps the uncertainty.
**Status:** holding. `burndown config` surfaces the active rates for correction.

### ADR-005 — The "budget stop" is a `check` command, never a process-killer
**Context:** The pitch includes "hard budget stops." A tool that force-kills a
running agent to enforce a budget is dangerous (data loss, broken jobs).
**Decision:** Burndown ships `burndown check` with meaningful exit codes
(0 ok / 1 projected-over / 2 already-over). You wire it into your own pre-run
hook or CI step and decide what to do. Burndown itself never kills anything.
**Why:** the user owns the kill decision; our job is the accurate signal.
**Status:** done.

### ADR-006 — Runway uses recent (24h) pace, not lifetime average
**Context:** "When do I run out?" should reflect how hard you're going *now*.
**Decision:** Runway = (budget − spent) / last-24h burn rate (falling back to
period average if there's no recent activity). Period average is shown alongside
for context.
**Why:** a quiet month shouldn't hide that today you're burning 5× normal.
**Status:** done for USD mode; token-mode recent-pace is a v0.2 refinement
(currently uses period average — noted in `forecast.py`).

### ADR-007 — Multi-currency via a static, configured FX rate (no live fetch)
**Context:** Users outside the US (the author is in India) want spend shown in
their own currency *alongside* USD — "according to current rates."
**Decision:** Show a secondary currency (e.g. INR) next to USD everywhere, using
a USD→X rate stored in config (`burndown currency INR`). Burndown does **not**
fetch live rates — that would open a network connection and break the core
guarantee.
**Why:** the zero-network promise (ADR-002) is the product's trust story *and*
the #1 user requirement; a convenience FX call isn't worth compromising it. The
rate is a one-line config edit. A future **opt-in** `burndown fx` refresh — the
lone, user-triggered, data-free network call — is on the roadmap but off by
default.
**Status:** done; defaults shipped for common currencies, rate overridable.

### ADR-008 — v0.1 counts ALL Claude usage, not just programmatic (known gap)
**Context:** The June-2026 credit pool meters *programmatic* usage (Agent SDK /
`claude -p` / Actions) specifically; interactive Claude Code usage is on the
regular subscription quota.
**Decision:** v0.1 sums every billable event. The logs carry an `entrypoint`
field that should let us split programmatic vs interactive — deferred to v0.2.
**Why:** total burn is still useful and honest today; the programmatic-only
filter is the right next refinement for the credit-pool use case.
**Status:** documented limitation; v0.2 work item.
