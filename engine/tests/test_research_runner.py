import copy

import numpy as np
import pandas as pd
import pytest

from traderlab.research_engine.runner import evaluate, validate
from traderlab.synthetic import make_bars


@pytest.fixture
def job():
    return dict(kind="exploration", strategy="ema_adx_trend", version="1.0.0", params={},
                market="spot", symbol="BTCUSDT", interval="4h", period_start="2020-04-01T00:00:00Z",
                period_end="2020-05-01T00:00:00Z", capital=100000,
                costs=dict(fee_bps=10, spread_bps=2, slippage_bps=5))


def test_deterministic_spot_never_shorts(job):
    bars = make_bars(n=726)
    first = evaluate(job, bars)
    assert first == evaluate(job, bars)
    assert first["mode"] == "exploration"
    assert first["effective_params"]["allow_short"] is False
    assert all(t["side"] == "Long" for t in first["trades"])
    assert len(first["curves"]["equity"]) > 0


@pytest.mark.parametrize("change", [dict(kind="registered"), dict(period_end="2025-02-01T00:00:00Z"),
                                     dict(params={"allow_short": True}), dict(params={"slow": 1}),
                                     dict(params={"fast": 100, "slow": 100}), dict(version="9.0.0")])
def test_rejects_invalid_requests(job, change):
    with pytest.raises(ValueError):
        validate({**job, **change})


def test_rejects_gap_nan_and_truncated_period(job):
    bars = make_bars(n=726)
    for bad in (bars.drop(bars.index[600]), bars.iloc[:-10]):
        with pytest.raises(ValueError):
            evaluate(job, bad)
    bars.iloc[600, 0] = np.nan
    with pytest.raises(ValueError):
        evaluate(job, bars)


def test_futures_require_complete_funding(job):
    job = {**job, "market": "um"}
    bars = make_bars(n=726)
    with pytest.raises(ValueError):
        evaluate(job, bars)
    funding = pd.Series(0.0001, index=pd.date_range(job["period_start"], job["period_end"], freq="8h", inclusive="left"))
    result = evaluate(job, bars, funding)
    assert result["effective_params"]["allow_short"] is True
    with pytest.raises(ValueError):
        evaluate(job, bars, funding.iloc[1:])
    delayed = funding.copy()
    delayed.index = delayed.index + pd.Timedelta(milliseconds=15)
    delayed_result = evaluate(job, bars, delayed)
    assert delayed_result["funding_validation"]["max_delay_ms"] == 15
    delayed.index = delayed.index + pd.Timedelta(minutes=2)
    with pytest.raises(ValueError):
        evaluate(job, bars, delayed)
