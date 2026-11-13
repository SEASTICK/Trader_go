"""Data för agentlab: dagliga USDⓈ-M-perpar (OHLCV) och finansieringsränta ur de lokala Binance-arkiven (data.binance.vision).

Aldrig 2025 eller senare (slutprovet). Fler källor kopplas in med `register_source`. Survivorship: bara kontrakt som har arkiv lokalt.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

HOLDOUT = pd.Timestamp("2025-01-01", tz="UTC")           # exklusiv gräns: inget från detta datum läses någonsin
DATA_START = pd.Timestamp("2020-01-01", tz="UTC")
# Perioder. Builder/Quant itererar bara på `disc`. `valid` och `final` är förseglade och öppnas av Domaren.
PERIODS = {"disc": ("2020-10-01", "2022-12-31"), "valid": ("2023-01-01", "2023-12-31"), "final": ("2024-01-01", "2024-12-31")}


def period_slice(idx: pd.DatetimeIndex, name: str) -> np.ndarray:
    a, b = PERIODS[name]
    return (idx >= pd.Timestamp(a, tz="UTC")) & (idx <= pd.Timestamp(b, tz="UTC"))


@dataclass
class Panel:
    """Dagsstaplar (index: UTC-midnatt) per symbol. `funding` = summerad finansieringsränta per dag (positiv = long betalar)."""
    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    dvol: pd.DataFrame
    funding: pd.DataFrame
    meta: dict = field(default_factory=dict)
    funding_known: pd.DataFrame | None = None     # True där finansieringsutbetalningar faktiskt finns (inte ifyllt med 0). None = allt känt (syntetiska paneler)
    funding_rule: bool = True                     # datatäckningsregel v2: bara instrument med känd finansiering får handlas. False reproducerar körningarna R001-R004
    _cache: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self.funding_known is None:
            self.funding_known = pd.DataFrame(True, index=self.funding.index, columns=self.funding.columns)
        for df in (self.open, self.high, self.low, self.close, self.dvol, self.funding):
            if len(df) and df.index.max() >= HOLDOUT:
                raise ValueError("panelen innehåller data från slutprovet (2025 eller senare)")

    @property
    def symbols(self) -> list[str]:
        return list(self.close.columns)

    def cached(self, key, fn: Callable):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    # ---- kända funktioner, alla bara med data till och med dag t (ingen framtid) ----
    def ret(self, k: int) -> pd.DataFrame:
        return self.cached(("ret", k), lambda: self.close.pct_change(k, fill_method=None))

    def vol(self, k: int) -> pd.DataFrame:
        return self.cached(("vol", k), lambda: self.close.pct_change(fill_method=None).rolling(k, min_periods=max(5, k // 2)).std())

    def fund(self, k: int) -> pd.DataFrame:
        # features använder finansieringen till och med gårdagen (shift 1): dagens sista utbetalning sker vid själva beslutsögonblicket
        return self.cached(("fund", k), lambda: self.funding.shift(1).rolling(k, min_periods=max(2, k // 2)).mean())

    def universe(self, top_n: int = 30, min_age: int = 90) -> pd.DataFrame:
        """Handlingsbara dag t: minst `min_age` dagar gammal och bland de `top_n` största efter 30 dagars median omsättning (data till och med t).
        **Datatäckningsregel v2 (bestämd i förväg):** ett instrument får bara handlas dag t om finansieringsutbetalningar finns för minst 5 av de senaste 7 dagarna.
        Utan känd finansiering kan en position inte värderas, så instrumentet är inte handlingsbart (inget ifyllt med 0)."""
        def make():
            age = self.close.notna().cumsum()
            med = self.dvol.rolling(30, min_periods=20).median()
            med = med.where(age >= min_age)
            ok = self.close.notna()
            if self.funding_rule:
                known = self.funding_known.rolling(7, min_periods=1).sum() >= 5
                ok = ok & known
                med = med.where(known)
            rank = med.where(ok).rank(axis=1, ascending=False)
            return (rank <= top_n) & ok
        return self.cached(("uni", top_n, min_age, self.funding_rule), make)

    def fwd(self) -> pd.DataFrame:
        """Avkastning öppning(t+1) till öppning(t+2): det en position som beslutas på stängningen av dag t faktiskt tjänar."""
        return self.cached("fwd", lambda: (self.open.shift(-2) / self.open.shift(-1) - 1.0))

    def fwd_funding(self) -> pd.DataFrame:
        """Finansieringsränta som betalas under hållperioden för ett beslut på dag t (dag t+1:s utbetalningar)."""
        return self.cached("fwdfund", lambda: self.funding.shift(-1))


# ---------------------------------------------------------------- källor (pluggbara)
SOURCES: dict[str, dict] = {}


def register_source(name: str, loader: Callable | None, description: str, status: str = "available", needs: str = "") -> None:
    """Koppla in en datakälla. `loader(data_dir) -> DataFrame (dag × symbol)` eller None om den bara är föreslagen."""
    SOURCES[name] = {"loader": loader, "description": description, "status": status, "needs": needs}


def _um_symbols(data_dir: Path) -> list[str]:
    base = data_dir / "raw" / "binance" / "um"
    return sorted(p.name for p in base.iterdir() if (p / "1d").is_dir() and any((p / "1d").glob("*.zip"))) if base.exists() else []


def load_um_panel(data_dir: Path, *, symbols: list[str] | None = None, cache: Path | None = None) -> Panel:
    """Läser alla lokala USDⓈ-M-perpar (dagliga staplar, bundet till före 2025). Resultatet cachas som pickle."""
    from ..data import binance
    if cache is not None and cache.exists():
        with open(cache, "rb") as f:
            return pickle.load(f)
    syms = symbols or _um_symbols(data_dir)
    o, h, l, c, v, fu, fk = {}, {}, {}, {}, {}, {}, {}
    for s in syms:
        try:
            df = binance.load("um", s, "1d", data_dir, start=DATA_START, end=HOLDOUT)
        except FileNotFoundError:
            continue
        df = df[~df.index.duplicated(keep="first")]
        o[s], h[s], l[s], c[s], v[s] = df["open"], df["high"], df["low"], df["close"], df["volume"] * df["close"]
        try:
            f = binance.load_funding(s, data_dir, start=DATA_START, end=HOLDOUT)
            # dagen d = utbetalningar i (d 00:00, d+1 00:00]: en position som fylls vid öppningen 00:00 missar 00:00-utbetalningen vid inträdet och får den vid utträdet
            bucket = (f.index - pd.Timedelta(seconds=1)).normalize()
            fu[s] = f.groupby(bucket).sum()
            fk[s] = f.groupby(bucket).count() > 0                  # känd = minst en riktig utbetalning den dagen
        except FileNotFoundError:
            pass
    panel = Panel(pd.DataFrame(o).sort_index(), pd.DataFrame(h).sort_index(), pd.DataFrame(l).sort_index(), pd.DataFrame(c).sort_index(),
                  pd.DataFrame(v).sort_index(), pd.DataFrame(fu).reindex(pd.DataFrame(c).sort_index().index).reindex(columns=sorted(c)).fillna(0.0),
                  funding_known=pd.DataFrame(fk).reindex(pd.DataFrame(c).sort_index().index).reindex(columns=sorted(c)).fillna(False).astype(bool),
                  meta={"source": "data.binance.vision um 1d + fundingRate", "symbols": len(o), "funding_symbols": len(fu),
                        "caveat": "Bara kontrakt som har arkiv lokalt (survivorship). Slutprovet 2025+ är aldrig läst."})
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        with open(cache, "wb") as f:
            pickle.dump(panel, f)
    return panel


def synthetic_panel(n_days: int = 1500, n_assets: int = 25, seed: int = 0, momentum: float = 0.0, start: str = "2020-01-01") -> Panel:
    """Syntetisk panel för tester och kontroller. `momentum` > 0 planterar en riktig tvärsnittsmomentum-effekt (positiv kontroll)."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n_days, freq="D", tz="UTC")
    syms = [f"S{i:02d}USDT" for i in range(n_assets)]
    mkt = rng.normal(0.0003, 0.025, n_days)
    persistent = rng.normal(0, 1, n_assets)                 # varje tillgång har en långlivad "styrka"
    rets = np.zeros((n_days, n_assets))
    for t in range(n_days):
        drift = momentum * 0.004 * np.tanh(persistent + 0.0 * t)
        rets[t] = 0.6 * mkt[t] + rng.normal(0, 0.03, n_assets) + drift
        if t % 120 == 119:
            persistent = 0.7 * persistent + 0.7 * rng.normal(0, 1, n_assets)
    close = pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=idx, columns=syms)
    open_ = close.shift(1).fillna(close.iloc[0]) * (1 + rng.normal(0, 0.002, close.shape))
    high = np.maximum(open_, close) * 1.01
    low = np.minimum(open_, close) * 0.99
    dvol = pd.DataFrame(rng.uniform(5e7, 5e8, close.shape), index=idx, columns=syms)
    funding = pd.DataFrame(rng.normal(0.0003, 0.0002, close.shape), index=idx, columns=syms)
    return Panel(open_, high, low, close, dvol, funding, meta={"source": "syntetisk", "momentum": momentum})


register_source("um_ohlcv", None, "Dagliga USDⓈ-M-perpar (OHLCV) från data.binance.vision", "available")
register_source("um_funding", None, "Finansieringsränta per 8 timmar, summerad per dag", "available")
register_source("um_4h", None, "4h-staplar för samma kontrakt (finns lokalt, används inte ännu)", "available")
register_source("cm_quarterly", None, "COIN-M-kvartalsterminer (basis mot spot), finns lokalt delvis", "available")
register_source("um_metrics_oi", None, "Open interest och long/short-kvot (data.binance.vision futures/um/daily/metrics)", "proposed",
                "Dagsfiler per symbol; nedladdning via arkivet. Binance API är blockerat (451), så bara arkivet.")
register_source("um_liquidations", None, "Likvidationer", "proposed", "Finns inte som publikt arkiv på data.binance.vision.")
register_source("orderbook", None, "Orderbok (bookDepth) och spreadar", "proposed", "bookDepth-arkiv finns men är stort; kräver egen nedladdning.")
register_source("macro", None, "Makro (räntor, dollarindex, volatilitetsindex)", "proposed", "Kräver en öppen källa (FRED); inte vald än.")
register_source("sentiment", None, "Sentiment (Fear & Greed, sociala medier)", "proposed", "Kräver en öppen källa; inte vald än.")
