import pytest
from traderlab.research_engine.margin import liquidation_threshold

@pytest.mark.parametrize('q,margin,mmr,cost,funding,expected',[
    (10,1000,.005,0,0,0),(-10,1000,.005,0,0,199.00497512437812),
    (10,100,.005,0,0,90.45226130653268),(-10,100,.005,0,0,109.45273631840796),
    (10,100,.005,2,1,90.75376884422111),(-10,100,.005,2,1,109.15422885572139),
])
def test_hand_calculated_margin_equation(q,margin,mmr,cost,funding,expected):
    mark=liquidation_threshold(100,q,margin,cost,funding,mmr)
    assert mark==pytest.approx(expected)
    assert margin+q*(mark-100)-cost-funding==pytest.approx(abs(q)*mark*mmr,abs=1e-10)

def test_one_x_scope_is_not_exchange_exact_legacy_formula():
    assert liquidation_threshold(100,-10,1000)!=pytest.approx(100*(2-.005))
    assert liquidation_threshold(100,10,1000)!=pytest.approx(100*.005)
