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

## Maskininlärning (`traderlab/ml/`)

- `features.build_features`: avkastning över flera horisonter, volatilitet, trend, RSI, ATR, läge i
  intervallet, volym och kalender. Alla bara från historik (testas kolumn för kolumn mot look-ahead).
- `labels`: etiketten är exakt en affär. Beslut vid stängning av t, in vid öppning t+1, ut vid öppning t+1+h.
- `cv.PurgedKFold`: korsvalidering som gallrar överlappande etiketter och lägger till embargo.
- `walkforward.walk_forward_proba` / `ml_strategy`: tränas om med jämna mellanrum, bara på exempel vars utfall
  var kända vid tidpunkten. Modeller: `logistic` och `gbm`, med fast frö.
- Bevisat i testerna: hittar en signal som finns (påhittad AR-data, över 55 % rätt) och hittar **ingen** i ren
  slump (50 % ± 2). Klarar `check_no_lookahead`.

## Från motor till app

1. Registrera hypotesen i `research/registry.md` och committa.
2. Koppla rutan till hypotes, data och strategi i `research/experiments.json`:
   ```json
   {"E-01": {"hypothesis": "H-0001", "market": "spot", "symbol": "BTCUSDT", "interval": "4h",
             "strategy": {"name": "ml", "params": {"horizon": 1}},
             "costs": {"fee_bps": 10, "spread_bps": 2, "slippage_bps": 5}}}
   ```
   Strategier: `buy_and_hold`, `ma_cross`, `zscore_reversion`, `ml`.
   Riskskydd (valfritt, rekommenderas): `"risk": {"target_vol": 0.02, "max_drawdown": 0.25, "max_daily_loss": 0.05}`
   ger volatilitetsstyrd storlek, nödstopp och daglig förlustgräns utanför strategin (`traderlab/risk.py`).
3. `python -m traderlab batch` kör alla rutor med registrerad hypotes och ren data, och skriver
   `app/data/results.json`. Rutor utan resultat förblir `SIM` i appen. Rutor med resultat märks `HISTORIK`.

## Pappershandel framåt (`traderlab/paper/`)

Enligt skillen `papper-framat`. Inga riktiga order.

```python
from traderlab.paper import engine as paper
paper.freeze(repo, "P-0001", "H-0001", spec, planned_trades=60, stop_rule="förlust över 20 % eller avvikande takt")
```

- `freeze` kräver beslutet `READY_FOR_PAPER` för hypotesen i det committade registret. Specifikationen sparas i
  `paper/P-0001/strategy.json` med SHA-256 och registrets commit. Samma id kan inte frysas två gånger.
- `python -m traderlab paper step P-0001` loggar nya **stängda** staplar i `paper/P-0001/log.jsonl`. Raderna läggs bara
  till sist. Ändras strategin vägrar motorn fortsätta: det är en ny strategi.
- `python -m traderlab paper status P-0001` visar kapital, position, antal affärer och planerat antal.
- Bevisat: pappersresultatet blir **exakt** samma som backtestet på samma staplar, stegvis och i ett svep.

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
| Deflated Sharpe: sannolikhet att slå bästa tur efter N försök | `stats.deflated_sharpe` | `test_deflated_sharpe_falls_with_more_trials` |
| ML tränas bara på kända utfall, gallrad CV med embargo | `ml/` | `test_ml.py` |
| Batch kör bara registrerade rutor med ren data | `batch.run_all` | `test_batch.py` |
| Riskskydd: volatilitetsstyrd storlek, nödstopp, daglig förlustgräns, utan look-ahead | `risk.py` | `test_risk.py` |
| Papper: bara READY_FOR_PAPER, fryst, append-only, identiskt med backtest | `paper/engine.py` | `test_paper.py` |
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
