"""
burndown/money.py — currency formatting + USD→secondary conversion.

Conversion uses a STATIC, user-configured FX rate. There is deliberately NO
network call to fetch live rates — that would break burndown's zero-network
guarantee (see docs/DECISIONS.md ADR-007). Set yours with `burndown currency`.
"""
from __future__ import annotations

# code -> (symbol, rough default USD->code rate). Override the rate per your prefs.
KNOWN_FX: dict[str, tuple[str, float]] = {
    "USD": ("$", 1.0), "INR": ("₹", 83.0), "EUR": ("€", 0.92), "GBP": ("£", 0.79),
    "JPY": ("¥", 157.0), "CAD": ("C$", 1.37), "AUD": ("A$", 1.51), "SGD": ("S$", 1.35),
    "BRL": ("R$", 5.40), "CNY": ("¥", 7.20), "AED": ("AED ", 3.67), "ZAR": ("R", 18.5),
}


def fmt_usd(x: float) -> str:
    return f"${x:,.2f}"


def _second(usd: float, cfg) -> str | None:
    code = getattr(cfg, "currency2", "")
    rate = getattr(cfg, "fx_rate", 0.0)
    if not code or not rate:
        return None
    sym = getattr(cfg, "currency2_symbol", "") or (code + " ")
    return f"{sym}{usd * rate:,.0f}"


def dual(usd: float, cfg) -> str:
    """'$41.80 (≈ ₹3,469)' if a secondary currency is set, else '$41.80'."""
    s = _second(usd, cfg)
    return f"{fmt_usd(usd)} (≈ {s})" if s else fmt_usd(usd)


def money(x: float, cfg) -> str:
    """A point amount in the budget unit (dual-currency USD, or raw tokens)."""
    if getattr(cfg, "budget_unit", "usd") == "tokens":
        return f"{int(x):,} tok"
    return dual(x, cfg)


def rate(usd_per_day: float, cfg, suffix: str = "/day") -> str:
    """A rate, e.g. '$6.10/day (≈ ₹506/day)'."""
    if getattr(cfg, "budget_unit", "usd") == "tokens":
        return f"{int(usd_per_day):,} tok{suffix}"
    s = _second(usd_per_day, cfg)
    base = fmt_usd(usd_per_day) + suffix
    return f"{base} (≈ {s}{suffix})" if s else base
