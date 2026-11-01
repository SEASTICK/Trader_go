import pandas as pd

from traderlab import quality
from traderlab.synthetic import make_bars


def test_clean_synthetic_data_passes():
    rep = quality.check(make_bars(500, interval="4h", seed=1), "4h")
    assert rep.ok, rep.problems
    assert rep.missing_bars == 0 and rep.expected_rows == 500


def test_gap_detected_with_location():
    bars = make_bars(1000, seed=2).drop(index=make_bars(1000, seed=2).index[50:53])
    rep = quality.check(bars, "4h")
    assert rep.missing_bars == 3
    assert rep.largest_gaps[0][2] == 3
    assert rep.ok and any("saknade" in w for w in rep.warnings)  # liten lucka: varning, inte fel


def test_many_missing_bars_is_an_error():
    b = make_bars(200, seed=2)
    rep = quality.check(b.drop(index=b.index[10:20]), "4h")
    assert not rep.ok and any("1 %" in p for p in rep.problems)


def test_duplicates_and_order():
    bars = make_bars(100, seed=3)
    dup = pd.concat([bars, bars.iloc[[10]]])
    rep = quality.check(dup, "4h")
    assert rep.duplicates == 1 and rep.not_increasing >= 1


def test_bad_ohlc_nonpositive_and_negative_volume():
    bars = make_bars(100, seed=4)
    bars.iloc[5, bars.columns.get_loc("high")] = bars.iloc[5]["low"] * 0.5
    bars.iloc[6, bars.columns.get_loc("close")] = 0.0
    bars.iloc[7, bars.columns.get_loc("volume")] = -1.0
    rep = quality.check(bars, "4h")
    assert rep.bad_ohlc >= 1 and rep.non_positive_price == 1 and rep.negative_volume == 1


def test_outlier_and_stale_run():
    bars = make_bars(300, seed=5, vol=0.005)
    bars.iloc[100, bars.columns.get_loc("close")] *= 1.8
    bars.iloc[100, bars.columns.get_loc("high")] = bars.iloc[100]["close"]
    flat = bars.iloc[199]["close"]
    for i in range(200, 210):
        for col in ("open", "high", "low", "close"):
            bars.iloc[i, bars.columns.get_loc(col)] = flat
        bars.iloc[i, bars.columns.get_loc("volume")] = 0.0
    bars.iloc[210, bars.columns.get_loc("open")] = flat
    bars.iloc[210, bars.columns.get_loc("low")] = min(flat, bars.iloc[210]["low"])
    bars.iloc[210, bars.columns.get_loc("high")] = max(flat, bars.iloc[210]["high"])
    rep = quality.check(bars, "4h")
    assert any(t.startswith(str(bars.index[100])[:10]) for t, _ in rep.outliers)
    assert rep.stale_runs and rep.stale_runs[0][1] >= 6
    assert rep.ok and len(rep.warnings) == 2  # äkta kraschar och stillastående pris stoppar inte


def test_timezone_and_alignment():
    bars = make_bars(50, seed=6)
    naive = bars.tz_localize(None)
    assert not quality.check(naive, "4h").timezone_ok
    shifted = bars.copy()
    shifted.index = shifted.index + pd.Timedelta(minutes=30)
    assert quality.check(shifted, "4h").misaligned == 50


def test_markdown_report_mentions_result():
    md = quality.check(make_bars(50, seed=7), "4h").to_markdown("Test")
    assert "Resultat: **OK**" in md
