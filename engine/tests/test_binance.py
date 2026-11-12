import hashlib
import io
import zipfile

import pandas as pd
import pytest

from traderlab.data import binance


def _zip(name: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, text)
    return buf.getvalue()


ROW_MS = "1704067200000,42283.58,42554.57,42261.02,42475.23,1271.68,1704081599999,0,0,0,0,0"
ROW_US = "1735689600000000,93576.00,94509.42,93489.03,94401.14,1300.0,1735703999999999,0,0,0,0,0"


def test_urls():
    assert binance.kline_url("spot", "BTCUSDT", "4h", "2024-01") == \
        "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/4h/BTCUSDT-4h-2024-01.zip"
    assert binance.kline_url("um", "BTCUSDT", "1d", "2024-01").startswith(
        "https://data.binance.vision/data/futures/um/monthly/klines/")
    assert binance.months("2023-11", "2024-02") == ["2023-11", "2023-12", "2024-01", "2024-02"]


def test_parse_milliseconds_microseconds_and_header():
    df = binance.parse_klines_csv(f"{ROW_MS}\n{ROW_US}\n".encode())
    assert list(df.index) == [pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")]
    assert df.iloc[0]["close"] == pytest.approx(42475.23)
    with_header = binance.parse_klines_csv(f"open_time,open,high,low,close,volume,x,x,x,x,x,x\n{ROW_MS}\n".encode())
    assert len(with_header) == 1


def test_parse_funding():
    s = binance.parse_funding_csv(b"calc_time,funding_interval_hours,last_funding_rate\n1704067200000,8,0.00010000\n")
    assert s.iloc[0] == pytest.approx(0.0001)
    assert s.index[0] == pd.Timestamp("2024-01-01", tz="UTC")


def test_fetch_verifies_checksum_never_overwrites_and_records_missing(tmp_path):
    files = {}
    for m in ["2024-01", "2024-02"]:
        z = _zip(f"BTCUSDT-4h-{m}.csv", ROW_MS + "\n")
        url = binance.kline_url("spot", "BTCUSDT", "4h", m)
        files[url] = z
        files[url + ".CHECKSUM"] = f"{hashlib.sha256(z).hexdigest()}  BTCUSDT-4h-{m}.zip".encode()
    calls = []

    def opener(url):
        calls.append(url)
        if url not in files:
            raise OSError("HTTP Error 404: Not Found")
        return files[url]

    r = binance.fetch("spot", "BTCUSDT", "4h", "2024-01", "2024-03", tmp_path, opener=opener)
    assert len(r.downloaded) == 2 and r.missing == ["2024-03"]
    assert (tmp_path / "MANIFEST.md").read_text().count("BTCUSDT") == 1
    again = binance.fetch("spot", "BTCUSDT", "4h", "2024-01", "2024-02", tmp_path, opener=opener)
    assert len(again.skipped_existing) == 2 and not again.downloaded

    bad = dict(files)
    url = binance.kline_url("spot", "ETHUSDT", "4h", "2024-01")
    bad[url] = _zip("x.csv", ROW_MS)
    bad[url + ".CHECKSUM"] = b"0" * 64 + b"  x.zip"
    with pytest.raises(ValueError, match="Kontrollsumman"):
        binance.fetch("spot", "ETHUSDT", "4h", "2024-01", "2024-01", tmp_path, opener=lambda u: bad[u])
    assert not list((tmp_path / "raw/binance/spot/ETHUSDT/4h").glob("*.zip"))

    df = binance.load("spot", "BTCUSDT", "4h", tmp_path)
    assert len(df) == 2  # samma rad i båda månaderna: quality.check ska hitta dubbletten


def test_bounded_load_never_opens_holdout_archives(tmp_path):
    folder = tmp_path / "raw/binance/um/BTCUSDT/4h"
    folder.mkdir(parents=True)
    (folder / "BTCUSDT-4h-2024-01.zip").write_bytes(_zip("x.csv", ROW_MS))
    (folder / "BTCUSDT-4h-2025-01.zip").write_bytes(b"unreadable holdout")
    bounds = dict(start="2024-01-01T00:00:00Z", end="2025-01-01T00:00:00Z")
    assert len(binance.load("um", "BTCUSDT", "4h", tmp_path, **bounds)) == 1
    funding = folder.parent / "fundingRate"
    funding.mkdir()
    (funding / "BTCUSDT-fundingRate-2024-01.zip").write_bytes(_zip("x.csv", "1704067200000,8,0.0001"))
    (funding / "BTCUSDT-fundingRate-2025-01.zip").write_bytes(b"unreadable holdout")
    assert len(binance.load_funding("BTCUSDT", tmp_path, **bounds)) == 1
    with pytest.raises(ValueError, match="UTC"):
        binance.load("um", "BTCUSDT", "4h", tmp_path, start="2024-01-01")


def test_markpris_url_skiljer_sig_fran_kline_url():
    from traderlab.data import binance as b
    assert b.kline_url("cm-mark", "ADAUSD_201225", "1d", "2020-11").endswith("futures/cm/monthly/markPriceKlines/ADAUSD_201225/1d/ADAUSD_201225-1d-2020-11.zip")
    assert "/klines/" in b.kline_url("cm", "ADAUSD_201225", "1d", "2020-11")
