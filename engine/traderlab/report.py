"""Sammanfattning av ett backtest, med det som granska-backtest kräver."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from . import stats
from .backtest import BacktestResult


@dataclass
class Summary:
    total_return: float
    max_drawdown: float
    trades: int
    win_rate: float
    avg_trade: float
    t_trades: float          # t-värde per affär (förenklat)
    t_daily_nw: float        # t-värde på dagsavkastning med Newey-West
    sharpe: float
    sharpe_ci: tuple[float, float]
    exposure: float          # andel staplar med position
    turnover_per_year: float # handlat belopp per år, i gånger kapitalet
    costs: float
    funding: float
    liquidations: int
    attempts: int
    t_required: float
    passes: bool
    deflated_sharpe: float   # sannolikhet att resultatet slår bästa tur efter alla försök (0..1)

    def to_dict(self) -> dict:
        """Som ordlista för JSON. NaN (för lite data) blir None, eftersom NaN inte är giltig JSON."""
        def clean(v):
            if isinstance(v, float) and not np.isfinite(v):
                return None
            return v
        d = {k: clean(v) for k, v in asdict(self).items()}
        d["sharpe_ci"] = [clean(x) for x in self.sharpe_ci]
        return d


def summarize(res: BacktestResult, attempts: int, seed: int = 0) -> Summary:
    eq = res.equity
    rets = res.bar_returns
    daily = stats.daily_returns(rets)
    closed = res.closed_trades
    trade_rets = np.array([t.net_return for t in closed]) if closed else np.array([])
    pos = res.position
    turnover = float(np.abs(pos.diff().fillna(pos)).sum())
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9) if len(eq) > 1 else 1.0
    t_req = stats.t_krav(attempts)
    t_nw = stats.newey_west_t(daily)
    return Summary(
        total_return=float(eq.iloc[-1] - 1) if len(eq) else 0.0,
        max_drawdown=stats.max_drawdown(eq),
        trades=len(closed),
        win_rate=float((trade_rets > 0).mean()) if trade_rets.size else 0.0,
        avg_trade=float(trade_rets.mean()) if trade_rets.size else 0.0,
        t_trades=stats.t_stat(trade_rets),
        t_daily_nw=t_nw,
        sharpe=stats.sharpe(daily),
        sharpe_ci=stats.block_bootstrap_sharpe_ci(daily, seed=seed),
        exposure=float((pos != 0).mean()) if len(pos) else 0.0,
        turnover_per_year=turnover / years,
        costs=res.total_costs,
        funding=res.total_funding,
        liquidations=res.liquidations,
        attempts=attempts,
        t_required=t_req,
        passes=t_nw >= t_req,
        deflated_sharpe=stats.deflated_sharpe(daily.to_numpy(), max(attempts, 1)),
    )
