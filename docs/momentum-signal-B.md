# H-0017 leverans B – signalmodul mom-signal/1.0.0

Datum 2026-11-03. Underlag: [research/h0017-protokoll.md](../research/h0017-protokoll.md) §3–§5 och
[uppdraget](claude-uppdrag-momentum-B.md). Implementation för Codex granskning, inte godkänd. Endast syntetiska
indata har använts; ingen marknadshistorik har lästs och ingen H-0017-körning har startats.

## API

Modul: [engine/traderlab/momentum_signal.py](../engine/traderlab/momentum_signal.py). Konstant `VERSION = "mom-signal/1.0.0"`.

| Funktion | Indata | Utdata |
|---|---|---|
| `validate_bars(bars)` | 4H-kontraktsstaplar, index = öppningstid | ValueError vid fel; ändrar inget |
| `daily_closes(bars)` | som ovan | en rad per kalenderdag: `close` (20-stapelns close, NaN om dagen inte är komplett), `complete` |
| `signals(bars)` | som ovan | en rad per kalenderdag D med kolumnerna i `COLUMNS` |
| `latest_decision(sig, t)` | utdata från `signals`, tid t | senaste rad med `decision_time <= t`; KeyError om ingen |

Kolumner i `signals`: `decision_time` (D+1 00:00 UTC), `earliest_fill` (samma tid; första öppning nästa lager får
fylla vid), `close`, `s7`, `s14`, `s28`, `s`, `vol`, `cap`, `w_target`, `available`, `reason`, `version`.

Endast kolumnen `close` läses. `open`, `high` och `low` påverkar aldrig ett beslut.

## Tidsregler

- Stapel t omfattar [t, t+4h). Dag D är komplett med alla sex staplar 00–20; dagsclose är 20-stapelns close, känd vid D+1 00:00.
- Horisonter 7, 14 och 28 kalenderdagar; volatiliteten använder de 61 kalenderdagarna D−60..D. Positioner räknas i
  kalenderdagar, aldrig i antal observationer.
- Dagens beslut är inte känt på dagens egna staplar: `latest_decision` vid D 20:00 ger D−1.

## Otillgänglig signal

`available = False`, numeriska fält NaN och orsak, prövade i ordning:

| Orsak | När |
|---|---|
| `incomplete_day` | dag D saknar någon stapel, även en pågående sista dag |
| `warmup` | färre än 60 kalenderdagar före D i indata |
| `missing_day` | en dag i D−60..D är ofullständig (täcker även horisonternas uppslag) |
| `invalid_vol` | volatiliteten är inte ändlig och > 0, till exempel konstant pris |

Ingen ersättning med platt eller full vikt. I en bedömningsperiod är otillgänglighet OGILTIG_DATA för körlagret.
Fel som avvisas med ValueError: saknad `close`, index som inte är DatetimeIndex, naivt eller icke-UTC (även UTC+4,
som ligger på 4H-rutnätet), dubbletter, osorterat, tid utanför 4H-gränserna, icke-ändligt eller icke-positivt close.

## Verifiering

- [engine/tests/test_momentum_signal.py](../engine/tests/test_momentum_signal.py): 32 tester, alla godkända. Handräknade
  horisonter och mål (s = 0, 1/3, 2/3, 1; stigande, fallande, lika pris), volatilitet mot `statistics.stdev` och
  avgränsad mot ddof=0, 59/61 avkastningar, logavkastning, prisernas std och sqrt(252), första tillgängliga dag,
  dagsgräns och beslutstid, att bara 20-stapelns close räknas, pågående sista dag, prefix vid hel- och halvdag,
  ändrade framtida priser, ändrade open/high/low, saknad dag och saknad stapel, nollvolatilitet och 13 felaktiga indata.
- Hela motorsviten: 585 godkända med `engine/.venv/bin/python -m pytest`.
- Riktade felprov: 14 avsiktliga fel infördes ett i taget i modulen och testfilen kördes. Alla 14 fångades: beslut
  vid D 20:00, nästa dags close, observationer i stället för kalenderdagar, 60 stängningar, ddof=0, sqrt(252),
  ändrade vikter, logavkastning, lika pris ger 1, ofullständig dag tillåten, nollvolatilitet godkänd, tyst sortering,
  icke-UTC godkänd, 59 dagars uppvärmning. En femtonde mutant (full vikt vid nollvolatilitet inne i grenen vol > 0)
  var ekvivalent och kunde inte nås; den räknas inte. Felprovet med icke-UTC missades först, eftersom Stockholmsfallet
  stoppades av 4H-kontrollen; testet fick därför också en UTC+4-zon och krav på felmeddelande. Modulen återställdes
  och jämfördes byte för byte efter proven.

## Begränsningar

Endast syntetiskt prövat. Datakvalitet, 2025-skydd och OGILTIG_DATA-beslut ligger i körlagret (leverans E/G). Ingen
ledger, band, avsikt, fyllning, funding, marginal eller risk ingår (leverans C). Legacy-signalerna återanvänds
oförändrade senare och är inte en del av denna modul.
