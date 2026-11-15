# H-0026 (tidigare H-0017) leverans D2 – buy_and_hold (mom-bh/1.0.0)

Datum 2026-11-15. Underlag: [protokollet](../research/h0017-protokoll.md) §6, §8, §9, §11 och
[uppdraget](claude-uppdrag-momentum-D2.md). Hypotesen heter H-0026 på main sedan 2026-11-14
(`research/id-omnumrering.md`, commit `3cd3c4c`). Implementationen är för Codex granskning och inte godkänd. Bara
syntetiska minnesdata har använts, och inga körningar på verklig historik har gjorts. **D2 omfattar bara
buy_and_hold:s faktiska förlopp. MOM-D01 i övrigt och MOM-D02–D05 återstår.**

## API

| Del | Beskrivning |
|---|---|
| `momentum_benchmark.run_buy_and_hold(market, order, mmr, legacy_order, cost)` | ett buy_and_hold-konto med 100 000 genom hela horisonten. Kontonyckeln är `"buy_and_hold/{L1|L2}"`. Underlaget är D1:s låsta `momentum_control.Market`, som kontrolleras före och efter körningen. Ingen signal behövs, så ett konstant pris (vol = 0) avvisas inte |
| `BenchmarkRun` | policy, legacy-ordning, scenario, RunLog (close-, dags- och eventspår), antal ignorerade event före start och den förregistrerade regeln (`BH_RULE`) som källa för inträdet |

## Ändring i godkänd kod: eventmodulen (`momentum_event.py`)

- `Scenario` får fältet `policy`, `"momentum"` (standard) eller `"buy_and_hold"`. Momentumetiketten är
  oförändrad (`A-mmr0.05-c0.0016`), och buy_and_hold får prefixet `buy_and_hold-`. Eftersom funding- och
  marginaltillståndet binds till etiketten avvisas ett policybyte mitt i förloppet.
- `process_bar`: för buy_and_hold anropas inte `momentum_risk.step`. I stället ger `_bh_step` en normalavsikt med
  w = 1 vid första testöppningen (§6 på E_trade via oförändrad `risk.fill_intent`/ledger) och en terminalavsikt med
  w = 0 vid terminal, om kontot lever. Annars ges ingen avsikt. Det finns inget dagsbeslut, ingen cap, inget band och
  inget stopp. peak och day_start rörs inte och kan inte utlösa handel. Likvidation förs vidare som absorberande
  tillstånd, och en signal till buy_and_hold avvisas.
- Allt annat är den gemensamma, godkända kedjan: gap, A-funding, gapmarginal, fyllning, B-funding, intrastapelprövning,
  kronologisk funding, C5-01 och likvidation. Momentumvägen är oförändrad rad för rad, och alla tidigare
  momentumtester passerar oförändrade.
- **Följd för status:** MOM-C03 och MOM-C05 är återöppnade till in_progress för omgranskning av den ändrade
  eventmodulen. MOM-C04 (close- och boundgarantin) bedöms opåverkad, eftersom momentumvägen och BarResult inte ändras
  och boundtesterna passerar. Codex avgör.

## Verifiering

- [engine/tests/test_momentum_benchmark.py](../engine/tests/test_momentum_benchmark.py): 24 tester, alla godkända.
  Facit är oberoende Decimal och oraklet.
  - **O2:** q 998,4025559105431, kostnad 159,744…, E_trade 99 840,255…, och floatresten i C klipps inte. P ≠ M i båda
    riktningarna.
  - **Fasta enheter och ingen momentumrisk:** fall genom −2 %, −15 % och −20 % samt uppgång. q är oförändrat, och den
    enda kostnaden är inträdet. Betald och mottagen funding bokförs utan återinvestering. Ett momentumkonto på samma
    bana stoppar fortfarande. Vikten över 1 efter B-funding ombalanseras inte. Konstant pris godtas för buy_and_hold,
    men D1:s signalkrav består för momentum.
  - **O5/O16:** A/B × positiv, negativ och noll ränta vid T, T + 1 ms, T + 30 s, T − 30 s och T − 1 ms, vid första
    öppningen och vid midnatt.
  - **Event före start och 2025, ändrat underlag:** event före start ignoreras och räknas, och både 2025-event och
    ändrat underlag avvisas.
  - **O10 och full kalender:** alla åtta etiketter med skilda identiteter. Varje closepunkt och terminalkapitalet
    jämförs mot en oberoende Decimal-ledger med P ≠ M och sex fundingevent. L1/L2-spåren är identiska, och O10:s
    lokala terminal (FIXTUR) ger kostnad 60,864 och E 97 979,136.
  - **O11/O18:** tröskeln 0,52715789… efter 500 i betald funding. Publik gaplikvidation prövas på exakt floatgräns
    vid båda mmr, med negativt prövningskapital. Mmr-scenarierna skiljer sig vid 0,515. Intrastapelträff med blandad
    funding ger olösta event enligt C5-01. Därefter absorberande noll med likvidationsflagga, och ingen
    terminalavsikt för ett likviderat konto.
  - **Isolering, policybindning, fel och prefix.**
- **Reproducerbar felprovsmatris:** [scripts/momentum-d2-mutations.py](../scripts/momentum-d2-mutations.py) bygger på
  D1:s godkända klassning: grön baslinje, orörda mutant- och kontrollgrenar före all körning, självtest med nio fall
  och samma urval och ordning. Den kör D2-, event- och kontrollproven. Resultat i
  [docs/momentum-D2-mutationer.json](momentum-D2-mutationer.json): 23 fångade och 0 missade. Den första körningen
  gav två missar ("likvidation glöms i kontoregeln" och "delat kontoförlopp mellan legacy-ordningar"); proven
  kompletterades.
- **Hela verifieringen:** D2-matrisens `--check` ger PASS (23/0), och D1-matrisens `--check` ger PASS (31/0/1). 629 momentumtester och 1 182 motortester passerar, liksom A1-oraklet, 30 av 30 momentum-audits och alla fyra checklistor.

## Inte i D2

Legacy-konton, no_vol, old_mix/new_mix med delkonton, bruttoexponering och blandningarnas risklås samt alla
kontrollkontons diagnostiska bound återstår. Ingen statistik, inga kriterier och inga beslut. Det finns fortfarande
två öppna frågor till Edwin, D1-Q01 och D1-Q02, men ingen av dem behövs för D2.
