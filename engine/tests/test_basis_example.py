import pytest

from traderlab import basis_example as e


def test_exact_hedge_locks_the_usd_value_but_not_the_coin_count():
    r = e.hold_to_expiry(x_coins=10, spot0=100, fut0=102, contract_usd=10, expiry_prices=[150, 100, 50])
    assert r["contracts"] == 102 and r["notional_usd"] == 1020 and r["cost_usd"] == 1000
    for o in r["outcomes"]:
        assert o.usd_value == pytest.approx(1020)            # USD-värdet är låst vid X · F0
        assert o.return_on_cost == pytest.approx(0.02)       # premien på 2 %
        assert o.margin_ratio_at_expiry == pytest.approx(1.0)
    coins = [o.coins for o in r["outcomes"]]
    assert coins == pytest.approx([1020 / 150, 1020 / 100, 1020 / 50])   # 6,8 / 10,2 / 20,4 mynt: antalet mynt ändras


def test_integer_contracts_leave_a_residual_exposure():
    # 7 mynt · 102 USD = 714 USD = 71,4 kontrakt: 71 kontrakt säkrar inte hela positionen.
    r = e.hold_to_expiry(x_coins=7, spot0=100, fut0=102, contract_usd=10, expiry_prices=[150, 50])
    assert r["contracts"] == 71 and r["notional_usd"] == 710
    up, down = r["outcomes"]
    assert up.usd_value != pytest.approx(r["target_usd"]) and down.usd_value != pytest.approx(r["target_usd"])
    assert up.usd_value > down.usd_value   # kvarvarande 0,04 mynt ger kvarvarande prisexponering
    assert abs(up.usd_value - r["target_usd"]) < 0.03 * r["target_usd"]


def test_hedge_ratio_below_one_makes_the_result_follow_the_price():
    exact = e.hold_to_expiry(10, 100, 102, 10, [150, 50])
    half = e.hold_to_expiry(10, 100, 102, 10, [150, 50], contracts=51)   # halv säkring
    assert exact["outcomes"][0].usd_value == pytest.approx(exact["outcomes"][1].usd_value)
    assert half["outcomes"][0].usd_value > half["outcomes"][1].usd_value + 100


def test_example_table_is_generated_from_the_function():
    from traderlab.data import basis_report as r
    t = r.example_table()
    assert "| 10 mynt, 102 kontrakt (exakt säkring) | 150 | 6,800 | 1020,00 | 2,00% | 1,000 |" in t
    assert "heltalsavrundning" in t
