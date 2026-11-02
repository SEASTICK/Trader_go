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


def test_first_futures_month_uses_only_available_archives_and_reports_warmup(job, tmp_path, monkeypatch):
    import hashlib
    import io
    import json
    import zipfile
    from traderlab.research_engine import runner

    job = {**job, "market": "um", "period_start": "2020-01-01T00:00:00Z",
           "period_end": "2020-02-01T00:00:00Z"}
    bars = make_bars(n=186)
    bars.index = pd.date_range(job["period_start"], periods=186, freq="4h")
    rates = pd.Series(0.0001, index=pd.date_range(job["period_start"], periods=93, freq="8h"))
    # Verified cached archives; any download (especially 2019) is a regression.
    for frame, name, text in (
        ("4h", "BTCUSDT-4h-2020-01.zip", "\n".join(
            f"{int(t.timestamp()*1000)},{r.open},{r.high},{r.low},{r.close},{r.volume}"
            for t, r in bars.iterrows())),
        ("fundingRate", "BTCUSDT-fundingRate-2020-01.zip",
         "calc_time,funding_interval_hours,last_funding_rate\n" + "\n".join(
             f"{int(t.timestamp()*1000)},8,{v}" for t, v in rates.items())),
    ):
        folder = tmp_path / "raw" / "binance" / "um" / "BTCUSDT" / frame
        folder.mkdir(parents=True)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr(name.replace(".zip", ".csv"), text)
        raw = buf.getvalue()
        (folder / name).write_bytes(raw)
        (folder / (name + ".CHECKSUM")).write_text(hashlib.sha256(raw).hexdigest() + "  " + name)
    def no_download(*args, **kwargs):
        pytest.fail("Unexpected download outside verified first-month archives")
    monkeypatch.setattr(runner.binance, "fetch", no_download)
    output = tmp_path / "result.json"
    runner.run_job(job, tmp_path, output)
    result = json.loads(output.read_text())
    assert result["metadata"]["warmup_bars"] == 0
    assert result["metadata"]["warmup_start"] == "2020-01-01T00:00:00+00:00"
    assert len(result["metadata"]["source_files"]) == 2
    assert any("0 av 600" in w for w in result["warnings"])
    assert result["trades"] == []  # EMA 200 cannot be ready in 186 bars.
    first = output.read_bytes()
    runner.run_job(job, tmp_path, output)
    assert output.read_bytes() == first


@pytest.mark.parametrize('change',[{'params':{}},{'strategy':'bb_rsi_reversion'},{'period_end':'2026-01-01T00:00:00Z'},{'capital':200000},{'version':'9.0.0'}])
def test_registered_reproduction_cannot_change_protocol(change,tmp_path):
    from traderlab.research_engine.registered import run_job
    request=dict(kind='registered',hypothesis_id='H-0009',strategy='ema_adx_trend',version='1.0.0',
        params={'reproduction':'frozen_windows_v1'},market='um',symbol='BTCUSDT',interval='4h',
        period_start='2020-01-01T00:00:00Z',period_end='2025-01-01T00:00:00Z',capital=100000,
        costs={'fee_bps':10,'spread_bps':2,'slippage_bps':5})
    with pytest.raises(ValueError,match='protokollet'):run_job({**request,**change},tmp_path,tmp_path/'out.json')
