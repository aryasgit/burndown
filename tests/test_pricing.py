from burndown.pricing import cost_usd, rates_for


def test_cost_is_per_million():
    assert cost_usd("claude-opus-4-8", 1_000_000, 0, 0, 0) == 15.0   # input @ $15/M
    assert cost_usd("opus", 0, 1_000_000, 0, 0) == 75.0              # output @ $75/M
    assert cost_usd("opus", 0, 0, 1_000_000, 0) == 18.75            # cache write
    assert cost_usd("opus", 0, 0, 0, 1_000_000) == 1.5             # cache read


def test_family_match():
    assert rates_for("claude-opus-4-8")[0] == 15.0
    assert rates_for("claude-sonnet-4-6")[0] == 3.0
    assert rates_for("claude-haiku-4-5")[0] == 0.80


def test_unknown_falls_back_to_opus_not_cheaper():
    # never under-report: an unknown model is priced at the most expensive tier
    assert rates_for("some-future-model-x9") == rates_for("opus")


def test_override_wins():
    assert rates_for("opus", {"opus": [1, 2, 3, 4]}) == (1.0, 2.0, 3.0, 4.0)
