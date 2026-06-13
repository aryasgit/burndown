"""
burndown/logs.py — read Claude Code usage logs, privacy-safely.

SECURITY POSTURE (see docs/SECURITY.md — these are guarantees, not preferences):
  * READ-ONLY.  We only ever open log files for reading. We never write to, near,
    or over anything under your Claude directories.
  * CONTENT-BLIND.  We extract ONLY token-usage numbers + minimal metadata
    (model, timestamp, session id, project folder NAME, git branch). We never
    read, keep, or transmit the actual prompt/response text in `message.content`.
  * NO NETWORK.  This module makes no network calls. The only socket in the whole
    package is the opt-in loopback dashboard (serve), bound to 127.0.0.1; the tool
    cannot leak what it never sends.
  * DEFENSIVE.  Malformed lines, missing fields, and unreadable files are skipped,
    never fatal.

SCHEMA (verified against real ~/.claude/projects/**/*.jsonl):
  one JSON object per line; a *billable* event looks like
    {"type":"assistant", "uuid":..., "timestamp":"...Z", "sessionId":...,
     "cwd":..., "gitBranch":...,
     "message":{"model":"claude-opus-4-8",
                "usage":{"input_tokens":N,"output_tokens":N,
                         "cache_creation_input_tokens":N,"cache_read_input_tokens":N, ...}}}
  `uuid` is the per-message id; we de-duplicate on it so resumed/forked sessions
  (the same message re-logged in several files) are counted once.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class Event:
    ts: datetime
    session_id: str
    model: str
    input: int
    output: int
    cache_write: int
    cache_read: int
    project: str
    branch: str
    entrypoint: str
    uuid: str

    @property
    def total_tokens(self) -> int:
        return self.input + self.output + self.cache_write + self.cache_read

    @property
    def programmatic(self) -> bool:
        """True if this usage is programmatic (Agent SDK / `claude -p` / CI) — i.e.
        metered against the June-2026 credit pool — vs interactive app usage."""
        return is_programmatic(self.entrypoint)


# Entrypoints that mean "programmatic" (credit-pool) usage. Grounded in real logs:
# 'sdk-cli' is programmatic; 'claude-desktop' is interactive. Hint-matched so future
# programmatic entrypoints (github-actions, headless, ...) are caught; anything
# unrecognized is treated as interactive (won't falsely inflate pool usage).
_PROGRAMMATIC_HINTS = ("sdk", "cli", "action", "headless", "-p", "print", "api")


def is_programmatic(entrypoint: str) -> bool:
    e = (entrypoint or "").lower()
    return any(h in e for h in _PROGRAMMATIC_HINTS)


def find_log_files(dirs: list[str]) -> list[Path]:
    """Every *.jsonl under the configured roots.

    Resolves each path and drops any file that escapes its root — defense against
    a symlinked log directory pointing at something sensitive elsewhere on disk.
    """
    out: list[Path] = []
    for d in dirs:
        try:
            root = Path(d).expanduser().resolve()
        except OSError:
            continue
        if not root.is_dir():
            continue
        for p in root.rglob("*.jsonl"):
            try:
                rp = p.resolve()
                rp.relative_to(root)        # must stay inside its declared root
            except (OSError, ValueError):
                continue
            if rp.is_file():
                out.append(rp)
    return out


def _parse_ts(v) -> datetime | None:
    if not isinstance(v, str):
        return None
    try:
        dt = datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iter_events(dirs: list[str]) -> Iterator[Event]:
    """Yield one Event per billable assistant message, de-duplicated by uuid.

    Only usage + metadata are pulled off each record — message content is never
    touched.
    """
    seen: set[str] = set()
    for path in find_log_files(dirs):
        try:
            fh = path.open("r", errors="ignore")
        except OSError:
            continue
        with fh:
            for line in fh:
                # cheap pre-filter: skip the ~99% of lines with no usage block
                if '"usage"' not in line:
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if not isinstance(o, dict) or o.get("type") != "assistant":
                    continue
                msg = o.get("message")
                if not isinstance(msg, dict):
                    continue
                usage = msg.get("usage")
                if not isinstance(usage, dict):
                    continue
                model = str(msg.get("model") or "")
                if not model or model == "<synthetic>":
                    continue
                uid = str(o.get("uuid") or o.get("requestId") or "")
                if uid:
                    if uid in seen:
                        continue
                    seen.add(uid)
                ts = _parse_ts(o.get("timestamp")) or _parse_ts(msg.get("timestamp"))
                if ts is None:
                    continue
                cwd = str(o.get("cwd") or "")
                # Path(...).name handles both / and \ separators (cross-platform).
                project = (Path(cwd.replace("\\", "/")).name if cwd else "") or "—"
                yield Event(
                    ts=ts,
                    session_id=str(o.get("sessionId") or ""),
                    model=model,
                    input=_int(usage.get("input_tokens")),
                    output=_int(usage.get("output_tokens")),
                    cache_write=_int(usage.get("cache_creation_input_tokens")),
                    cache_read=_int(usage.get("cache_read_input_tokens")),
                    project=project,
                    branch=str(o.get("gitBranch") or ""),
                    entrypoint=str(o.get("entrypoint") or ""),
                    uuid=uid,
                )


def _int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0
