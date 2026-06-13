from burndown.config import Config
from burndown.money import dual, money, rate


def test_usd_only_when_no_secondary():
    assert dual(41.8, Config()) == "$41.80"


def test_dual_currency():
    cfg = Config(currency2="INR", currency2_symbol="₹", fx_rate=83.0)
    assert dual(100.0, cfg) == "$100.00 (≈ ₹8,300)"


def test_rate_formats_per_day():
    cfg = Config(currency2="INR", currency2_symbol="₹", fx_rate=83.0)
    assert rate(6.10, cfg) == "$6.10/day (≈ ₹506/day)"


def test_token_mode_ignores_currency():
    cfg = Config(budget_unit="tokens", currency2="INR", fx_rate=83.0)
    assert money(1500, cfg) == "1,500 tok"
