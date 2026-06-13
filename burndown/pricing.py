"""
burndown/pricing.py — turn tokens into dollars.

Rates are PER MILLION TOKENS, in USD, and are best-effort estimates. They are
USER-CONFIGURABLE (`burndown config` shows the active table; override it in
~/.config/burndown/config.toml). Anthropic changes pricing and exact rates are
deliberately NOT pinned here.

Two honesty guarantees:
  * The burn-rate and runway MATH is correct regardless of the rates — prices
    only scale the dollar figures.
  * If you'd rather not trust a dollar estimate at all, budget in raw tokens
    (`burndown budget N --tokens`) and the forecast ignores pricing entirely.

Unknown models fall back to the most expensive tier (Opus) so we never quietly
UNDER-report what you're spending.
"""
from __future__ import annotations

# model-key -> (input, output, cache_write, cache_read) per 1,000,000 tokens, USD
DEFAULT_PRICING: dict[str, tuple[float, float, float, float]] = {
    "opus":   (15.0, 75.0, 18.75, 1.50),
    "sonnet": (3.0,  15.0, 3.75,  0.30),
    "haiku":  (0.80, 4.0,  1.0,   0.08),
}
_FALLBACK = DEFAULT_PRICING["opus"]


def _coerce(v) -> tuple[float, float, float, float]:
    if isinstance(v, dict):
        return (float(v.get("input", 0)), float(v.get("output", 0)),
                float(v.get("cache_write", 0)), float(v.get("cache_read", 0)))
    try:
        t = tuple(float(x) for x in v)
    except (TypeError, ValueError):
        return _FALLBACK
    return (t + _FALLBACK)[:4]


def rates_for(model: str, overrides: dict | None = None) -> tuple[float, float, float, float]:
    name = (model or "").lower()
    table = {**DEFAULT_PRICING, **(overrides or {})}
    if name in table:                       # exact full-id override wins
        return _coerce(table[name])
    for key in ("opus", "sonnet", "haiku"):  # else match by family
        if key in name and key in table:
            return _coerce(table[key])
    return _coerce(table.get("opus", _FALLBACK))


def cost_usd(model: str, input_t: int, output_t: int, cache_write_t: int,
             cache_read_t: int, overrides: dict | None = None) -> float:
    i, o, cw, cr = rates_for(model, overrides)
    return (input_t * i + output_t * o + cache_write_t * cw + cache_read_t * cr) / 1_000_000.0
