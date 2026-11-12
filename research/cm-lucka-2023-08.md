# Kan luckan 2023-08-28 till 2023-08-31 i COIN-M återfinnas i Binances dagsarkiv?

Skriven 2026-11-12 på uppdrag av granskaren (Codex, PR #112). **Inget backtest är kört, inget från 2025 eller senare är
läst, och ingen interpolation, inget sista-kända-pris och ingen annan börs har använts.** Bara Binances originalfiler
(data.binance.vision), verifierade mot sina publicerade SHA-256-checksummor.

## Svar

**Ja. Luckan går att stänga med verifierade originalstaplar, utan motsägelser.**

- **72 av 72** saknade kontraktdagar (18 kontrakt × 4 dagar) finns som originalfil i Binances dagsarkiv
  (`data/futures/cm/daily/klines/<kontrakt>/1d/`), alla med giltig checksumma.
- Alla 72 staplar har tidsstämpel exakt dagens start (00:00 UTC), konsistent OHLC (low ≤ open/close ≤ high) och volym ≥ 0.
- På de **72** dagar som finns i *både* dagsarkivet och månadsfilerna (grannar: 2023-08-26/27 och 2023-09-01/02) är
  dagsfilen **exakt lika** med månadsfilen i open, high, low, close och volym. Dagsarkivet motsäger alltså inte månadsfilerna.
- Spot (nio USDT-par) har aldrig haft luckan: alla 36 spot-gapdagar finns i spot-månadsfilerna, och 36 av 36 dagsfiler är exakt lika med dem (`spot_gap_days_equal_to_monthly` i rapportfilen).
- Efter att de 72 staplarna lagts in återstår **0 luckor** i de 18 kontrakten fram till förfallodagen.
- Staplarna är inte tomma: ingen har noll volym (median 73 458 kontrakt), öppningen hänger ihop med föregående stängning
  (ingen avvikelse över 2 %), och dagen 2023-08-29 innehåller en riktig kursrörelse (BTCUSD_230929: high 28 211 mot
  öppning 26 169). Luckan dolde alltså en volatil dag och inte en stilla.

**Orsaken till att dagarna saknas i månadsfilerna är inte fastställd.** Dagsfilerna finns, så det är månadsarkivets
sammanställning som saknar dem. Mer än så vet jag inte.

## Vad detta inte visar

- Dagsarkiv och månadsarkiv kommer från samma utgivare (Binance). Överensstämmelsen visar att de är inbördes konsekventa
  och att filerna inte är korrupta (checksumma), men inte att Binances data är fria från fel som finns i bägge.
- Kontrollen gäller bara dessa kontrakt och dagar. Andra luckor (till exempel 2022-02-26 till 2022-02-28 i USDⓈ-M-
  evighetsterminerna som drabbade H-0021) är **inte undersökta här**, men samma metod är tillämplig och kan prövas separat.
- Det avgör inte kostnader, marginal, kapacitet eller förtida upphörande. De fyra villkoren i PR #112 kvarstår, utom att
  villkor 2 (luckan) nu har en källbelagd lösning.

## Resultat per kontrakt (genererat ur `research/coverage/cm-gap-2023-08.json`)

Tabellerna skapas av `python -m traderlab.data.gapcheck` (från `engine/`, hämtar bara augusti–september 2023).

| Kontrakt | Gapdagar med verifierad originalstapel | Checksumma ok | Konsistent stapel | Grannar lika med månadsfil | Kvarvarande luckor till förfall |
|---|---|---|---|---|---|
| ADAUSD_230929 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| ADAUSD_231229 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| BCHUSD_230929 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| BCHUSD_231229 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| BNBUSD_230929 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| BNBUSD_231229 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| BTCUSD_230929 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| BTCUSD_231229 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| DOTUSD_230929 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| DOTUSD_231229 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| ETHUSD_230929 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| ETHUSD_231229 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| LINKUSD_230929 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| LINKUSD_231229 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| LTCUSD_230929 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| LTCUSD_231229 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| XRPUSD_230929 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |
| XRPUSD_231229 | 4/4 | 4/4 | 4/4 | 4/4 | 0 |

| Spot | Gapdagar i månadsfilen | Gapdagar med verifierad dagsfil | Grannar lika med månadsfil |
|---|---|---|---|
| BTCUSDT | 4/4 | 4/4 | 4/4 |
| ETHUSDT | 4/4 | 4/4 | 4/4 |
| ADAUSDT | 4/4 | 4/4 | 4/4 |
| BCHUSDT | 4/4 | 4/4 | 4/4 |
| BNBUSDT | 4/4 | 4/4 | 4/4 |
| DOTUSDT | 4/4 | 4/4 | 4/4 |
| LINKUSDT | 4/4 | 4/4 | 4/4 |
| LTCUSDT | 4/4 | 4/4 | 4/4 |
| XRPUSDT | 4/4 | 4/4 | 4/4 |


## Proveniens

- Varje stapel i den sammanslagna serien bär `source` = `monthly` eller `daily` (`traderlab.data.gapcheck.combined`).
  Månadsfilen vinner alltid där den har en stapel, och en dagsstapel läggs bara in för en dag som månadsfilen saknar.
- Varje dagsfil är hämtad från `https://data.binance.vision/data/<marknad>/daily/klines/<symbol>/1d/<symbol>-1d-<datum>.zip`,
  verifierad mot `<fil>.CHECKSUM` och sparad under `data/raw/binance/cm-daily/` (COIN-M) och `data/raw/binance/spot-daily/` (spot).
  URL, SHA-256 och storlek per fil finns i rapportfilen. Månadsfilerna är noterade i `data/MANIFEST.md`.
- En fil utan giltig checksumma sparas och används aldrig (testat).

## Förslag till fail-closed-regel i ett framtida protokoll

1. **Primär källa är månadsfilen.** En saknad dag får fyllas bara med dagsarkivets originalfil för samma kontrakt och dag,
   och bara om (a) checksumman stämmer, (b) tidsstämpeln är exakt dagens start, (c) OHLC är konsistent och volymen ≥ 0, och
   (d) dagsfilen är exakt lika med månadsfilen på de dagar som finns i bägge (grannkontrollen, maskinellt kontrollerad).
2. **Alla andra luckor ger `OGILTIG`.** Saknas en dag i både månads- och dagsarkivet, eller faller någon kontroll, avbryts
   körningen enligt `strict_gaps` (PR #111). Inget fylls med interpolation, sista kända värde eller annan börs.
3. **Reglerna gäller alla kontrakt och datum lika och kontrolleras maskinellt före körning**, inte efter att avkastning setts.
   Datum väljs aldrig bort.
4. **Staplar efter förfallodagen ignoreras** (kontrakt har staplar med noll volym efter förfallet).

## Avgränsning

- Hämtat: 18 kontrakt × 8 dagar (2023-08-26 till 2023-09-02) i COIN-M, och 9 spot-par × 8 dagar, plus spot-månadsfilerna för
  2023-08 och 2023-09. Inget från 2025 eller senare, inga avkastningar och ingen basis.
- Inget ändrar H-0020, H-0021 eller något protokoll.
