# Forskningsmotorn (`engine/`)

Python-paketet `traderlab`: hämtar öppen historik, kontrollerar den, kör backtest och räknar ut om ett
resultat kan vara tur. **Bara historik och papper.** Inga order, inga börskonton, inga nycklar.

## Kom igång

```bash
cd engine
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
```

## Kommandon

```bash
# Hämta 4h-staplar för BTC (spot) från Binance publika datafiler. Kontrollsumma verifieras, inget skrivs över.
.venv/bin/python -m traderlab fetch --symbol BTCUSDT --interval 4h --start 2021-01 --end 2024-12

# Finansieringsränta för terminer
.venv/bin/python -m traderlab fetch --market um --symbol BTCUSDT --interval 4h --start 2021-01 --end 2024-12 --funding

# Kvalitetskontroll (skillen hamta-data). Avslutas med fel om något behöver tittas på.
.venv/bin/python -m traderlab check --symbol BTCUSDT --interval 4h

# Krav på t-värde efter N försök
.venv/bin/python -m traderlab krav 17
```

Rådata hamnar i `data/raw/` (committas inte). `data/MANIFEST.md` får en rad per hämtning (committas).

## Köra ett experiment

```python
from pathlib import Path
from traderlab.costs import CostModel
from traderlab.data import binance
from traderlab.experiment import run_experiment
from traderlab import quality

repo = Path("..").resolve()
bars = binance.load("spot", "BTCUSDT", "4h", repo / "data")
print(quality.check(bars, "4h").to_markdown())

def strategi(b):  # målposition per stapel, bara data till och med stängningen
    ...

run_experiment("H-0001", repo, bars, strategi, CostModel(fee_bps=10, spread_bps=2, slippage_bps=5),
               market="spot BTCUSDT", interval="4h")
```

`run_experiment` **vägrar** om `H-0001` inte finns i den committade versionen av `research/registry.md`,
eller om registret har ocommittade ändringar (regel 2 i `CLAUDE.md`). Den vägrar också om strategin tittar
framåt. Resultatet sparas i `research/results/H-0001-<tid>.json` och skrivs aldrig över.

## Vad motorn garanterar (och testar)

| Regel | Var | Test |
|---|---|---|
| Beslut på stängd stapel, fyllning vid nästa öppning | `backtest.run` | `test_decision_at_close_fills_next_open`, `test_cannot_trade_on_the_bar_that_made_the_signal` |
| Avgift, spread och slippage på båda sidor | `costs.CostModel`, `backtest.run` | `test_costs_charged_on_both_sides_exactly` |
| Stresstest av kostnader (2,5×) | `experiment.run_experiment` | `test_run_experiment_writes_result_with_stress_and_control` |
| Finansieringsränta: long betalar, short tar emot | `backtest.run` | `test_funding_paid_by_long_received_by_short` |
| Likvidation från stapelns högsta/lägsta (isolerad marginal) | `backtest.run` | `test_liquidation_from_bar_high_isolated_margin` |
| Ingen look-ahead | `backtest.check_no_lookahead` | `test_lookahead_detected_and_honest_strategies_pass` |
| Slumpade positioner ger inget t-värde före kostnader | `experiment.random_label_control` | `test_random_labels_have_no_edge_before_costs` |
| Hypotes registrerad och committad före körning | `registry.require_registered` | `test_registry_and_experiment.py` |
| t-krav: Bonferroni, ensidigt, minst 2,0 | `stats.t_krav` | `test_t_krav_matches_skill_and_app` |
| Newey-West-t på dagsavkastning, Sharpe med block-bootstrap | `stats`, `report.summarize` | `test_stats.py` |
| Datakontroller: luckor, dubbletter, OHLC, noll/negativa priser, utstickare, stillastående pris, UTC, tidsjustering | `quality.check` | `test_quality.py` |
| Kontrollsumma, aldrig överskriven rådata, ms och µs-tidsstämplar | `data.binance` | `test_binance.py` |

## Begränsningar (än så länge)

- Hämtningen är bara provad mot låtsade svar. Den riktiga Binance-servern har inte gått att nå från
  Claudes molnmiljö (nätverket nekade `data.binance.vision`). På er egen dator fungerar det normalt.
- Exempelstrategierna i `traderlab/strategies/examples.py` är **inte** hypoteser. De finns för tester.
- Likvidationen är förenklad: isolerad marginal, likvidationspris från inträdespriset, ingen likvidationsavgift.
- Ingen gallring mellan träning och test än, eftersom inga modeller tränas. Det behövs när en etikett tittar framåt.
- Antal försök räknas som antal olika id i registret. Skillen `ny-hypotes` säger "alla rader". Se PR:en.
