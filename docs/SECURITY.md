# Security & privacy

Burndown reads your local Claude Code usage logs. Those logs contain your actual
prompts, code, and responses. So the bar here is high, and the design is built
around one idea: **the tool can't leak what it never sends, never stores, and
never even reads.**

## Guarantees

1. **No network — ever.** Burndown opens no sockets and imports no networking
   module (`socket`, `http`, `urllib`, `ssl`, no third-party HTTP client). There
   is no telemetry, no analytics, no update check, no "anonymous usage stats."
   You can verify in one command:
   ```
   grep -REn "^[[:space:]]*(import|from)[[:space:]]+(socket|ssl|urllib|http|httpx|requests)" burndown/
   ```
   (returns nothing — every import in the package is Python stdlib.)

2. **Content-blind.** The parser (`burndown/logs.py`) pulls only token-usage
   integers and minimal metadata: model name, timestamp, session id, the project
   folder **name** (not its path contents), and git branch. It never reads,
   keeps, or emits `message.content` — your prompts and code are never touched.

3. **Read-only on your logs.** Log files are opened for reading only. Burndown
   never writes to, renames, or deletes anything under your Claude directories.

4. **Writes, in full:** exactly two, both local and both yours —
   - `~/.config/burndown/config.toml` (chmod `600`), only when you run
     `burndown budget`/config;
   - an HTML report file, only when you run `burndown report`. The report
     contains aggregate numbers only — **no conversation content** — and is
     git-ignored by default.

5. **No secrets.** Burndown never reads `.env` files, API keys, `auth.json`,
   credential stores, or anything outside the configured log directories.

6. **Path-confined.** Log discovery resolves symlinks and drops any file that
   escapes its declared root — a symlinked log dir can't trick Burndown into
   reading elsewhere on disk.

7. **No code execution.** No `eval`, `exec`, `pickle`, or shell-out on log data.
   The only subprocess-like action is none in v0.1.

## Threat model (what we defend against)

| Threat | Mitigation |
|---|---|
| Tool exfiltrates prompts/code | content-blind parser + no network (#1, #2) |
| Supply-chain compromise via a dependency | zero runtime dependencies (ADR-001) |
| Tool corrupts/loses Claude logs | strictly read-only (#3) |
| Malicious symlink redirects reads | path confinement (#6) |
| Budget enforcer kills a running job → data loss | enforcement is a `check` you act on, never an auto-kill (ADR-005) |
| Crafted/garbage log line crashes the tool | every parse is wrapped; bad lines skipped |

## Reporting

Found something? Open a private security advisory on the repo, or email
the maintainer. Please don't file public issues for vulnerabilities.
