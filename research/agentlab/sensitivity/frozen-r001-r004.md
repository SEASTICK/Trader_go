# Fryst känslighetskontroll: R001–R004-kandidaterna på den rättade grunden

**EFTERHANDSDIAGNOSTIK / UTFORSKANDE. Inte en bekräftelse och ingen ny hypotes. R001-R004 och registret är oförändrade.**

Period: 2020-10-01..2022-12-31 (discovery). Panelen läses med end=2023-01-01; arkiv från 2023 och senare öppnas inte.
Panel: 166 USDT-perpar (2020-01-01 till 2022-12-31); gamla panelens perpar: 85; täckningsluckor mot arkivlistan under discovery: 0 (kontrollerad: True).

Reproducera: `python -m traderlab.agentlab sensitivity` (kräver lokala rådata). Parametrarna läses ur `experiments.jsonl` och kontrolleras mot registrets nyckel; inget skrivs till registret eller `state.json`.

**Steg:** A = registrets gamla discovery-siffror (119 kontrakt inkl. 34 leveranskontrakt, gamla regler). B = samma 85 perpar med nuvarande regler (effekten av reglerna). C = hela panelen med nuvarande regler (effekten av de saknade kontrakten). t = medelvärde/(std/√n) för dagliga nettoavkastningar (`stats.t_stat`, samma metod som övriga projektet; för A härlett ur registrets Sharpe och n, vilket är identiskt). Funding > 0 betyder kostnad, < 0 intäkt. "Överlever" (endast beskrivning, trösklar satta före körningen): giltig täckning, Sharpe ≥ 1.0, t ≥ 2.0 och Sharpe > 0 med 2,5× kostnader.

**Sammanfattning:** 2 av 4 kandidater överlever på hela panelen (C); 4 av 4 med bara de gamla perparna och nuvarande regler (B); 4 har giltig täckning i C.

## X-0081 · ensemble_rank · `610bac07a444` (R002, dåvarande utfall PROMISING)

Parametrar: `{"members": ["xs_mom", "funding_carry", "lowvol"], "q": 0.3, "rebal": 3}`

| Mått (discovery) | A: registret (gammalt) | B: gamla perpar, nya regler | C: hela panelen, nya regler |
|---|---|---|---|
| Universum (symboler i panelen / aldrig valbara / någonsin hållna) | 119 / – / – | 85 / 75 / 74 | 166 / 99 / 97 |
| Valbara per dag (medel / min) | – | 30.00 / 30 | 30.00 / 30 |
| Täckning / status | ej mätt (tyst noll) | GILTIG  | GILTIG  |
| Okänd data (andel av bruttoexponering: saknad kurs / okänd finansiering) | ej mätt | 0.1 % / 0.0 % | 0.2 % / 0.0 % |
| Nettoavkastning per år | 44.6 % | 55.6 % | 44.6 % |
| Sharpe | 1.74 | 2.08 | 1.60 |
| t | 2.61 | 3.12 | 2.40 |
| Största nedgång | -15.7 % | -19.0 % | -23.3 % |
| Omsättning (gånger/år) | 63.9 | 62.7 | 63.4 |
| Finansiering per år | -6.2 % | -7.3 % | -8.0 % |
| Sharpe med 2,5× kostnader | 1.37 | 1.72 | 1.26 |
| Överlever (beskrivning) | – | ja | ja |

## X-0082 · ml_xs · `0051738937c5` (R002, dåvarande utfall REJECT)

Parametrar: `{"model": "lgbm", "h": 3, "q": 0.3, "retrain": 60, "uni": 30}`

| Mått (discovery) | A: registret (gammalt) | B: gamla perpar, nya regler | C: hela panelen, nya regler |
|---|---|---|---|
| Universum (symboler i panelen / aldrig valbara / någonsin hållna) | 119 / – / – | 85 / 75 / 72 | 166 / 99 / 94 |
| Valbara per dag (medel / min) | – | 30.00 / 30 | 30.00 / 30 |
| Täckning / status | ej mätt (tyst noll) | GILTIG  | GILTIG  |
| Okänd data (andel av bruttoexponering: saknad kurs / okänd finansiering) | ej mätt | 0.2 % / 0.0 % | 0.2 % / 0.0 % |
| Nettoavkastning per år | 39.8 % | 39.8 % | 30.2 % |
| Sharpe | 1.65 | 1.62 | 1.18 |
| t | 2.48 | 2.43 | 1.77 |
| Största nedgång | -13.9 % | -18.1 % | -22.6 % |
| Omsättning (gånger/år) | 103.7 | 101.4 | 100.0 |
| Finansiering per år | 2.1 % | 0.6 % | -1.0 % |
| Sharpe med 2,5× kostnader | 1.01 | 1.00 | 0.59 |
| Överlever (beskrivning) | – | ja | nej |

## X-0122 · ensemble_rank · `2d3d4d5026e5` (R003, dåvarande utfall REJECT)

Parametrar: `{"members": ["xs_mom", "funding_carry", "lowvol"], "q": 0.2, "rebal": 7}`

| Mått (discovery) | A: registret (gammalt) | B: gamla perpar, nya regler | C: hela panelen, nya regler |
|---|---|---|---|
| Universum (symboler i panelen / aldrig valbara / någonsin hållna) | 119 / – / – | 85 / 75 / 72 | 166 / 99 / 93 |
| Valbara per dag (medel / min) | – | 30.00 / 30 | 30.00 / 30 |
| Täckning / status | ej mätt (tyst noll) | GILTIG  | GILTIG  |
| Okänd data (andel av bruttoexponering: saknad kurs / okänd finansiering) | ej mätt | 0.3 % / 0.1 % | 0.2 % / 0.1 % |
| Nettoavkastning per år | 56.8 % | 63.5 % | 51.2 % |
| Sharpe | 1.71 | 1.82 | 1.43 |
| t | 2.56 | 2.73 | 2.15 |
| Största nedgång | -22.7 % | -22.4 % | -30.2 % |
| Omsättning (gånger/år) | 46.2 | 46.5 | 46.9 |
| Finansiering per år | -6.6 % | -8.2 % | -9.4 % |
| Sharpe med 2,5× kostnader | 1.50 | 1.61 | 1.23 |
| Överlever (beskrivning) | – | ja | ja |

## X-0173 · bab · `108fb9dfbab8` (R004, dåvarande utfall REJECT)

Parametrar: `{"vt": 0.2, "k": 60, "q": 0.3, "rebal": 7, "uni": 50}`

| Mått (discovery) | A: registret (gammalt) | B: gamla perpar, nya regler | C: hela panelen, nya regler |
|---|---|---|---|
| Universum (symboler i panelen / aldrig valbara / någonsin hållna) | 119 / – / – | 85 / 84 / 82 | 166 / 127 / 123 |
| Valbara per dag (medel / min) | – | 48.92 / 31 | 48.94 / 31 |
| Täckning / status | ej mätt (tyst noll) | GILTIG  | GILTIG  |
| Okänd data (andel av bruttoexponering: saknad kurs / okänd finansiering) | ej mätt | 0.2 % / 0.0 % | 0.2 % / 0.0 % |
| Nettoavkastning per år | 39.9 % | 35.3 % | 21.9 % |
| Sharpe | 1.70 | 1.45 | 0.95 |
| t | 2.56 | 2.17 | 1.42 |
| Största nedgång | -21.3 % | -23.4 % | -26.3 % |
| Omsättning (gånger/år) | 32.4 | 34.7 | 32.8 |
| Finansiering per år | 0.5 % | 0.2 % | 0.3 % |
| Sharpe med 2,5× kostnader | 1.49 | 1.23 | 0.73 |
| Överlever (beskrivning) | – | ja | nej |

## Avvikelser mot R001–R004 (förklaring utan regeljusteringar)

| Kandidat | ΔSharpe A→B (regler, 85 perpar) | ΔSharpe B→C (saknade kontrakt) | ΔSharpe A→C (totalt) | Δnetto/år A→C |
|---|---|---|---|---|
| X-0081 ensemble_rank | +0.34 | -0.48 | -0.14 | +0.0 procentenheter |
| X-0082 ml_xs | -0.04 | -0.44 | -0.48 | -9.5 procentenheter |
| X-0122 ensemble_rank | +0.11 | -0.38 | -0.27 | -5.6 procentenheter |
| X-0173 bab | -0.26 | -0.50 | -0.76 | -18.0 procentenheter |

- **A→B** isolerar reglerna: leveranskontrakten (34 av 119 kolumner) är borta, universum och rankning bygger bara på USDT-perpar, kontrakt utan känd finansiering blir inte valbara och okänd data debiteras i stället för att bli noll. Skillnaden ska läsas som "vad de gamla siffrorna hade varit med dagens motor", inte som en förbättring.
- **B→C** isolerar de 81 perpar som saknades i R001–R004 (de fanns bara inte lokalt). De ändrar topp-30/50-urvalet och därmed vikterna; i discovery låg 7 % (2020–2021) och 19,7 % (2022) av de gamla platserna utanför ett korrekt universum.
- Registrets siffror (A) är återskapade med den gamla motorn och stämde mot auditen (`audits/coverage-R001-R004.json`); inga regler eller parametrar har justerats för att rädda eller fälla någon kandidat.
- **Urvalsfel kvarstår.** De fyra är de som överlevde R001–R004:s cirka 170 discovery-utvärderingar och är därför utvalda på just den här perioden. Trösklarna ovan är inte justerade för antalet försök (ingen DSR räknades om här), så "överlever" betyder bara "försvinner inte av universumskorrigeringen", inte att kanten är bekräftad. De två ensemblerna (X-0081, X-0122) har samma medlemmar och är starkt korrelerade, alltså i praktiken en och samma upptäckt.
- Valid (2023), final (2024) och 2025+ är inte öppnade. Inget i den här rapporten är en ny hypotes eller ett skäl att köra något av dem.

