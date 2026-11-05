"""Forskningsmotorerna får aldrig öppna arkiv från slutprovet (2025 och framåt)."""
import io
import zipfile

import pandas as pd

from traderlab import basis, xsbig, xsrun


def _zip(rows: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", rows)
    return buf.getvalue()


def _klines(month: str) -> str:
    days = pd.date_range(month + "-01", periods=5, freq="1D", tz="UTC")
    return "\n".join(f"{int(d.timestamp() * 1000)},100,101,99,100,10,{int(d.timestamp() * 1000) + 86399999},0,0,0,0,0"
                     for d in days) + "\n"


def _put(folder, name, ok_month="2024-12"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}-{ok_month}.zip").write_bytes(_zip(_klines(ok_month)))
    (folder / f"{name}-2025-01.zip").write_bytes(b"slutprov: far inte oppnas")


def test_research_loaders_never_open_holdout_archives(tmp_path):
    raw = tmp_path / "raw/binance"
    for sym in ("BTCUSDT", "ETHUSDT"):
        _put(raw / "spot" / sym / "1d", f"{sym}-1d")
        _put(raw / "um" / sym / "1d", f"{sym}-1d")
        f = raw / "um" / sym / "fundingRate"
        f.mkdir(parents=True)
        (f / f"{sym}-fundingRate-2024-12.zip").write_bytes(_zip("1733011200000,8,0.0001\n"))
        (f / f"{sym}-fundingRate-2025-01.zip").write_bytes(b"slutprov")
        _put(raw / "um" / f"{sym}_250328" / "1d", f"{sym}_250328-1d")
    (raw / "um-symbols.json").write_text('["BTCUSDT_250328", "ETHUSDT_250328"]')
    # Varje läsare skulle krascha på det oläsbara 2025-arkivet om det öppnades.
    o, c, v, fund = xsbig.load_panel(tmp_path, ["BTCUSDT", "ETHUSDT"])
    assert o.index.max() < pd.Timestamp("2025-01-01", tz="UTC") and len(fund["BTCUSDT"]) == 1
    xsrun.load_panel(tmp_path, ["BTCUSDT"])
    spot, futs = basis.load("BTCUSDT", tmp_path)
    assert spot.index.max() < pd.Timestamp("2025-01-01", tz="UTC") and list(futs) == ["BTCUSDT_250328"]
