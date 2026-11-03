# Momentummodell efter H-0013 – protokollutkast A1

Datum 2026-11-03. Status: **A1, granskningsutkast till Codex. Inte registrerat, inte godkänt, ingen registerrad.**
Hypotes-id tilldelas först i A2 efter att Codex godkänt exakt denna revision; här skrivs det `H-XXXX`.

Underlag: [forskningsplanen](h0013-efterfoljare-forskningsplan-20261103.md) (f43c1e7),
[metodgranskningen](momentum-metodgranskning-20261103.md) och
[kontraktsutkast 0.1](momentum-implementationskontrakt-utkast.md) (e55340a). Utkast 0.1 används som föreslagen
semantik. Där detta protokoll avviker eller preciserar står det i metodtabellen (§1) med skäl, skrivet före
implementation och före något resultat. H-0013 förblir REJECT. H-0016 och dess protokoll är orörda och räknas
fortsatt som ett försök.

Handräknade kontrollfall finns i §16; talen räknas om av `scripts/momentum-a1-oracles.py` till
[momentum-a1-orakel.json](momentum-a1-orakel.json). Oraklet använder bara syntetiska tal och är en räknekontroll
av formlerna, inte strategimotorn.

## 0. Versioner och identitet

| Del | Version i A1 | Vid A2 |
|---|---|---|
| Protokoll | `momentum-protokoll/A1` | `momentum-protokoll/1.0.0`, kopplat till id och registreringscommit |
| Signal | `mom-signal/1.0.0` | oförändrad om A1 godkänns |
| Ledger och utförande | `mom-ledger/1.0.0` | oförändrad om A1 godkänns |
| Resultat | `mom-result/1.0.0` | oförändrad om A1 godkänns |

Inga regler i §2–§15 får ändras mellan godkänd A1 och A2. A2 lägger bara till id, N, t-krav, registreringscommit
och statuskoppling. Ingen modell får köra under H-0013:s jobbkontrakt eller låsta RPC.

## 1. Metodtabell – avvikelser och preciseringar

Källa P = forskningsplanen, K = utkast 0.1. "Precisering" betyder att källan var öppen eller tvetydig.

| # | Ämne | Källa säger | Detta protokoll | Skäl |
|---|---|---|---|---|
| D01 | Funding/handel på samma gräns | K03: funding före affär som huvud, känslighet efter; klassificering öppen | Scenario A (funding på ingående q) och B (funding på q efter fyllning) är båda beslutsscenarier. MORE_RESEARCH kräver att alla kriterier gäller i A **och** B, varje scenario med sina egna jämförelser. A är rapporterat huvudscenario. | M01. Dagliga normalfyllningar sker kl 00:00, samma tid som avräkning, så ordningen påverkar systematiskt. Ett gynnsamt scenario kan inte väljas efteråt. |
| D02 | Mark-price-källa | P §6: ny mark-data får eget tilläggsmanifest | Återanvänd det redan verifierade mark-datasetet `54a5ca8f…` (68 arkiv, 10 962 staplar, ingen 2025-fil). Ingen ny nedladdning. | Det finns, är SHA-kontrollerat och har täckningskontroll mot kontraktsdatasetet. |
| D03 | Markpris vid funding | K03: exakt avräkningsmarkpris från fryst källa | Gränshändelse: `mark_open` för 4H-stapeln som börjar vid avräkningen. Mellanliggande händelse: se §8.3. | Historiskt avräkningsmarkpris finns inte i de publika arkiven. `mark_open` är närmaste observerade värde och märks som approximation. |
| D04 | Marginal/likvidation | K06: öppen blockerare | Uttryckligen avgränsad korsmarginalmodell, fast underhållssats 5 % (och 0,5 % redovisat), likvidation = hela kontots kapital förloras. Ingen historisk trappa påstås. §9. | Historiska trappor och avgifter får inte gissas. För huvudmodellen (long, w ≤ 1) är likvidation matematiskt utesluten utom vid stor ackumulerad betald funding; satsen är därför inte resultatkritisk där. |
| D05 | Tvetydighet i jämförelser | saknas | T-regeln (§8.4): när OHLC/tid inte avgör utfallet får huvudmodellen det ogynnsamma och jämförelserna det gynnsamma utfallet i kriterierna. | Konservativt för beslutet: en tvetydighet kan bara göra MORE_RESEARCH svårare. |
| D06 | Volatilitetscap och band | P §4.4: vikt över cap "får minska oavsett band"; K05: cap fast till nästa hela dag | Capbrott kontrolleras bara vid dagsbeslutet: w_current > cap_D ger minskning till w_target oavsett band. Ingen kontroll av volcap vid 4H-stängningar inom dygnet. | Ingen intradagsvolatilitet får smygas in. Viktdrift inom dygnet är liten och sker utan dold handel. |
| D07 | Normalavsikt samtidigt som riskexit | K03: får inte kombineras | Normalavsikten med samma fyllningstid stryks, skjuts inte upp. Nästa normala inträde kräver nästa dagsbeslut. | Ingen återupplivad gammal avsikt. Exempel O6. |
| D08 | Legacy-storlek | K07: ska låsas; gamla motorn: notional = kapital före avgift | Legacy-inträde storleksätts med K04-lösaren till |w| = 1 efter kostnad och markvärde; enheterna ligger sedan fast till utgång. Signal, riktning, ATR-stop och spärr efter stop oförändrade. | M02/M04: samma kapital- och kostnadsbas som alla konton; gamla motorn gav exponering något över 1×. |
| D09 | Legacy-funding | gamla motorn: per stapel till kontraktsöppning | Samma händelsebaserade funding till markpris som övriga konton. | En gemensam ledger. Gamla H-0013-nyckeltal kopieras därför inte (K07). |
| D10 | Legacy intrastapel-bound | K06: får inte använda post-exit low som om positionen fanns, men inte anta gynnsam ordning | Stopstapel: lägsta mark med positionen kvar ingår i bounden. Endast diagnostik för jämförelser. §10.2. | Stop utlöses på kontraktspris; mark/kontrakt-vägen är inte observerbar, så att mark-lägsta inträffat före stop kan inte uteslutas. Den strängare läsningen väljs och märks. |
| D11 | DSR | K08: öppen blockerare | Två försöksantal (registrerade id respektive full sökhistorik), två variansval, endast diagnostik. §14. | Beroende mellan försök är inte verifierat; intervallet redovisas i stället för en punktsiffra. |
| D12 | Fördröjningsstress | K08: +4h, ersättningsregel saknas | Senaste normalavsikt ersätter äldre; riskavsikter slås ihop efter prioritet; terminal ej fördröjd. §12. | Ingen växande orderhög. |
| D13 | Datafel | P §5: blockera nya köp och logga | Ofullständigt rutnät, saknad mark- eller fundingdata eller otillgänglig signal på en testdag stoppar körningen före beräkning: OGILTIG_DATA. | Strängare. En körning med blockerade köp kan inte ge ett jämförbart resultat. |
| D14 | Implementationsfel | P kriterium 6: riskregelöverträdelse = underkänt | Brott mot invarianterna i §13.3 ger OGILTIG, sparas och räknas. Omkörning av samma frysta hypotes kräver granskad rättelse, som H-0003. Likvidation i huvudkontot är däremot ett ekonomiskt underkännande (REJECT). | Ett kodfel är inte ett ekonomiskt utfall. |
| D15 | Stresser | P §6 | Kostnads-, funding- och fördröjningsstress körs bara för huvudmodellen. Kostnadsstress ingår i kriterierna, i både A och B. Funding- och fördröjningsstress är diagnostik. | Enligt P; jämförelser stressas inte. |
| D16 | Startläge för legacy | saknas | Legacy-konton, köp-och-behåll och momentumkonton får fylla vid första testöppningen om signalen från uppvärmningen redan anger position. | Lika behandling. Ingen position före testet. |

## 2. Hypotes och omfattning

En fast riskstyrd tidsseriemomentummodell på BTCUSDT, long eller platt, med lika vikt över 7, 14 och 28 dagars
signal, 60 dagars volatilitetscap mot 10 % årlig målrisk, 2 procentenheters handelsband, 2 % dagsstopp och 15 %
permanent stopp, ger positiv nettoavkastning efter kostnader och funding, och högre Sharpe än köp-och-behåll, varje
ensam komponent och båda förregistrerade blandningar, med högst 20 % uppmätt drawdown.

Vald efter H-0001–H-0016 på samma redan sedda BTC-historik. Parametrarna kommer från litteraturen och
forskningsplanen utan sökning, men valet är inte blint (§14.3). Ingen period i detta protokoll är en ren
bekräftelse. Ingen parameteroptimering, short, ATR-stop, take-profit, regimväljare eller ML i huvudmodellen.

## 3. Data

| Del | Källa | Kontroll före beräkning |
|---|---|---|
| Kontrakt-OHLC 4H | Binance USDⓈ-M BTCUSDT, fryst dataset `6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c` (120 arkiv, samma som H-0013/H-0016) | SHA/CHECKSUM per arkiv, fullständigt 4H-rutnät 2020-01-01 00:00–2024-12-31 20:00, giltig OHLC |
| Funding | Samma dataset, `fundingRate`-arkiven | Varje händelse har tid < 2025-01-01, ändlig ränta; antal gräns- och mellanhändelser rapporteras |
| Mark-OHLC 4H | `markPriceKlines`, dataset `54a5ca8f7895639586252889dbcdf993bd3c5a6a2443d9407bc10e277cf1818c` enligt [verifieringen](../data/audits/fas1-20261102/mark-price/verification.json) och [återvinningsmanifestet](../data/audits/fas1-20261102/mark-price/recovery-manifest.json) | Samma öppningstider som kontraktet för alla teststaplar, giltig OHLC, inga dubbletter |

- Endast [2020-01-01, 2025-01-01) UTC får läsas, för varje ingång inklusive funding, mark och jämförelser. Indata som
  når 2025 avvisas innan något räknas (som `fas2.check_development`). Inga 2025-arkiv öppnas.
- Uppvärmning: signal och volatilitet behöver kontraktsclose från 2021-11-01 (61 dagsstängningar före 2022-01-01).
  Legacy-indikatorer beräknas från 2020-01-01 som i H-0013.
- Om någon kontroll faller startar ingen beräkning: OGILTIG_DATA (D13). Ingen interpolering, framåtfyllning eller
  ersättning av mark med kontraktspris.
- Datasetens innehåll är inte omläst i A1; att kontrollerna passerar är en förutsättning som verifieras i leverans E.

## 4. Tid och horisont

- Stapel b har öppningstid t_b (UTC) och omfattar [t_b, t_b+4h). Dess close är känd vid t_b+4h.
- Dag D består av staplarna 00, 04, 08, 12, 16, 20 och är känd vid D+1 00:00. Dagsclose C_D = close för 20-stapeln.
- Första testöppning 2022-01-01 00:00. Före den: E = 100 000, q = 0, C = 100 000. Första dagsbeslut använder dag
  2021-12-31 och fylls vid 2022-01-01 00:00.
- Terminal: öppningen 2024-12-31 20:00. Alla konton stänger helt där med kostnad. Inga köp vid eller efter terminal.
  Dagsbeslutet vid 2025-01-01 00:00 skapas inte. Ingen 2025-stapel öppnas.
- Testperioden har 1 096 dagar (365 + 365 + 366). Halvår 2022H1–2024H2 är bara rapportgrupper; inget nollställs.
- Dagsavkastning: r_D = E_end(D)/E_end(D−1) − 1, där E_end(D) är markvärderat kapital vid close av dag D:s 20-stapel
  (före gap, funding och handel vid D+1 00:00). E_end(2021-12-31) = 100 000. Sista dagen slutar med terminalt
  kapital. Gap, funding och affärer vid 00:00 tillhör det nya dygnet. Startpunkten är ingen extra avkastningsdag.

## 5. Signal

För varje dag D, med kontraktsclose:

- s_h(D) = 1 om C_D / C_(D−h) − 1 > 0, annars 0, för h ∈ {7, 14, 28} kalenderdagar. Lika pris ger 0.
- s(D) = (s_7 + s_14 + s_28)/3 ∈ {0, 1/3, 2/3, 1}.
- r_i = C_i/C_(i−1) − 1 för de 60 senaste dagarna i ≤ D; vol(D) = std(ddof=1) × √365.
- cap(D) = min(1, 0,10/vol(D)). w_target(D) = s(D) × cap(D).
- Signalen är otillgänglig om någon av de 61 stängningarna saknas eller vol(D) inte är ändlig och > 0. I
  testperioden är det OGILTIG_DATA (D13); någon division med noll sker inte.

Exempel O12: s = 2/3 och vol = 60 % ger w_target = 0,1111.

## 6. Konto, enheter och kostnad

**Ledger.** Varje konto har kontantekvivalent C och enheter q (q < 0 bara för legacy-short). Nettokapital
E = C + q × M, där M är markpris. C innehåller insättning, realiserat resultat, alla kostnader och all funding och kan
bli negativ för en long; den är inte bokstavlig kassa. Genomsnittligt inträdespris sparas bara för redovisning av
realiserat resultat (partialminskning realiserar endast sålda enheter).

**Kostnad.** c = (10 + 2/2 + 5)/10 000 = 0,0016 per sida, stress 0,0040. En affär Δq till kontraktspris P bokförs en
gång: C ← C − Δq × P − c × P × |Δq|. Spread och slippage läggs inte också på priset.

**Storlek (K04).** Vid fyllning med beslutad vikt w, kapital E före affär (efter gap och scenario A-funding), q_old,
kontraktsöppning P och markvärde M = mark_open:

1. Kostnadsfri lösning q0 = w(E − q_old(M − P))/(M − w(M − P)). Om q0 = q_old handlas inget.
2. Gren: köp om q0 > q_old med k = M − P − cP, annars sälj med k = M − P + cP.
3. q_new = w(E − q_old × k)/(M − w × k).
4. Avvisa (fel, ingen klippning) om E ≤ 0, P ≤ 0, M ≤ 0, nämnaren ≤ 0, grenen inte stämmer med q_new eller
   q_new har annat tecken än w. w = 0 ger q_new = 0 med kostnad cP|q_old|.

Då gäller q_new × M / E_after = w exakt, där E_after = E + Δq(M − P) − cP|Δq|.

**Avrundning.** Kontinuerliga enheter i float64, ingen lot-, tick- eller minimibeloppsavrundning (modellbegränsning).
Jämförelser mot gränser görs på beräknade float-värden utan extra epsilon. Testtolerans för identiteter: relativ
avvikelse ≤ 1e−12 i vikt och belopp.

**Partial fill.** Varje avsikt fylls helt vid en tillåten öppning. Med "partial" menas här en delvis ökning eller
minskning av en befintlig position (O4). Ingen ofylld rest eller likviditetsgräns modelleras (begränsning).

## 7. Avsikter, band och risk (huvudmodellen och momentumkonton)

**Vid varje 4H-close (gränsen T):**

1. E_close = C + q × mark_close. Uppdatera peak = max(peak, E_close); peak startar på 100 000 före första kostnaden.
2. Permanent stopp om E_close/peak − 1 ≤ −0,15: full stängning vid öppningen T, kontot platt till terminal.
3. Dagsstopp om E_close/day_start − 1 ≤ −0,02: full stängning vid öppningen T. lock_day = dagen för stapeln som
   stängde. Inga köp med fyllningstid inom lock_day.

**Vid dagsbeslutet (close av 20-stapeln, T = D+1 00:00), efter steg 1–3:**

| Villkor, i ordning | Avsikt |
|---|---|
| permanent stopp aktivt eller nyss utlöst | ingen ny avsikt utöver stängningen |
| s(D) = 0 och q > 0 | full stängning (risk, oavsett band) |
| w_current > cap(D) | minska till w_target (risk, oavsett band) |
| abs(w_target − w_current) ≥ 0,02 | normal ombalansering till w_target |
| annars | hold_units |

w_current = q × mark_close/E_close vid samma close. Avsikten fryser w, inte q. Beslutstid, källdata och
avsiktstyp sparas före nästa pris. Högst en normal ombalansering per dygn följer av att normalbeslut bara tas här.

**Sammanslagning vid fyllningstid T.** Högst ett fill-event per konto och öppning. Prioritet: terminal > permanent
stopp > dagsstopp > capbrott/platt signal > normal. Om någon riskavsikt finns vid T stryks normalavsikten (D07).
Riskavsikter kan aldrig öka |q|. Ett köp är otillåtet om fyllningstiden ligger i lock_day eller efter permanent stopp.

**Dagsreset vid 00:00:** day_start(ny dag) = E_close för föregående dags 20-stapel. lock_day upphör att gälla för
den nya dagen. Ett redan köat riskutträde fullföljs. Permanent stopp återställs aldrig.

Viktdrift: med C ≥ 0 är w ≤ 1 efter prisrörelser; betald funding kan ge w något över 1, vilket nästa dagsbeslut
korrigerar som capbrott.

## 8. Eventordning

### 8.1 Gränsen T (close av stapel b−1 = öppning av stapel b)

| Steg | Händelse | Tillhör |
|---|---|---|
| 0 | E_close(b−1) till mark_close; peak; permanent stopp; dagsstopp (§7) | dag för b−1 |
| 1 | Om T = 00:00: dagsbeslut (§7), sedan dagsreset | beslut: gamla dagen; reset: nya |
| 2 | Gappunkt: E till mark_open(b) med q_old | dag för b |
| 3 | Scenario A: funding för gränshändelser vid T på q_old | dag för b |
| 4 | Likvidationskontroll vid gappunkten (§9) | dag för b |
| 5 | En sammanslagen fyllning vid kontraktsöppning P(b), storlek enligt §6 med M = mark_open(b) | dag för b |
| 6 | Scenario B: funding för gränshändelser vid T på q_new | dag för b |
| 7 | Spara C, q, E_after med fas `after_fill` | dag för b |

### 8.2 Inom stapel b

q är konstant för huvud- och momentumkonton. Inga beslut från high/low. Mark-extremer används för
likvidationskontroll och intrastapel-bound (§10). Legacy-stop kontrolleras på kontraktets high/low (§11).

### 8.3 Fundinghändelser

- Belopp = q × M_ref × ränta; positivt belopp betalas. Samma händelse bokförs exakt en gång per scenario.
- Gränshändelse: avräkningstid t med abs(t − T) < 60 s för en 4H-gräns T. M_ref = mark_open för stapeln som börjar vid T.
- Mellanhändelse: övriga. För huvud- och momentumkonton är q entydigt. M_ref = mark_high för betalning och
  mark_low för mottagande (huvudmodellen, ogynnsamt); jämförelser i kriterier får motsatt val (T-regeln).
- För legacy i en stapel med stop gäller T-regeln även för om positionen fanns vid händelsen.
- Antal mellanhändelser rapporteras. Det är inte verifierat i A1 att BTCUSDT saknar sådana.

### 8.4 T-regeln och klassificering mellan scenarier

1. Där OHLC eller tidsstämplar inte avgör ett utfall räknas huvudkontot med det ogynnsamma och varje jämförelse
   med det gynnsamma utfallet, när kriterierna C3–C5 prövas. Båda redovisas.
2. Scenario A och B körs fullständigt, med alla konton och kostnadsstress. Kriterierna (§13) prövas separat i A och B.
3. MORE_RESEARCH kräver alla kriterier sanna i A och i B. Om A och B ger olika utfall blir beslutet REJECT med
   flaggan `ordningskanslig = true`. Rapporterade huvudsiffror är A.

## 9. Marginal och likvidation (avgränsad modell)

- Ett konto per strategi(delkonto), korsmarginal, USDT som säkerhet, en position. Hela E är säkerhet.
- Underhållskrav MM = mmr × |q| × m med fast mmr = 0,05 i beslutet; mmr = 0,005 redovisas. Inga trappor,
  ingen likvidationsavgift, ingen ADL. Detta är en uttrycklig modellgräns, inte Binances historiska regler.
- Likvidationsvillkor E(m) = C + q × m ≤ mmr × |q| × m, prövat vid gappunkten och vid ogynnsam mark-extrem inom stapeln
  (mark_low för long, mark_high för short) med det q som kan ha funnits. Long: m ≤ −C/(q(1 − mmr)).
  Short: m ≥ C/(|q|(1 + mmr)).
- Vid träff: kontots E sätts till 0 och kontot är platt till terminal (konservativt).
- Huvudmodellen: varje träff gör C6 falskt (REJECT). Med w ≤ 1 är C ≥ 0 efter fyllning, och träff kräver betald
  funding som närmar sig positionsvärdet (O11: tröskel ≈ 0 vid w = 1; 0,527 efter 500 i betald funding).
- Jämförelser: kriterievärdet för ett jämförelsekonto (och dess blandning) är det högsta Sharpe av körning med
  och utan likvidationsmodellen (T-regeln). Båda redovisas.
- Kontrollexempel O11: legacy-short w = −1 vid 100 likvideras vid mark ≥ 190,48 (mmr 5 %) respektive 199,00 (0,5 %);
  det senare stämmer med `research_engine/margin.py` för samma isolerade uppställning.

## 10. Två riskserier

### 10.1 Stängningsserien (beslut och C6)

Punkter: startkapital 100 000 vid 2022-01-01 00:00 (fas `start`), E_close vid varje stapelclose 2022-01-01 00:00 –
2024-12-31 16:00 och terminalt E efter fyllning 2024-12-31 20:00. max_dd_close = min(E/löpande max − 1) med start
inkluderad. Den gamla `stats.max_drawdown` anropas bara med en serie som redan börjar med 100 000; funktionen ändras inte.

### 10.2 Intrastapel-bound (C6 för huvudmodellen, diagnostik för övriga)

Huvud- och momentumkonton, per stapel med konstant q efter öppningens steg: punkter i ordningen E(mark_open) före
fyllning, E_after, E(mark_high), E(mark_low), E(mark_close) för long (high före low, ogynnsam ordning för drawdown).
Hypotetisk peak uppdateras med high innan low jämförs. Startkapital och terminalpunkt ingår. Benämns *bound*, inte
observerad drawdown. Den styr inga stopp.

Legacy med ATR-stop i stapeln (long; short spegelvänt med mark_high som ogynnsam):

- Stop inom stapeln (kontraktsöppning > S): punkter E(mark_open), E(mark_high) och E(mark_low) med q kvar, sedan E efter
  stopfyllning vid S med kostnad. Mark-lägsta räknas med positionen kvar eftersom ordningen inte är observerbar (D10).
- Gap förbi stop (kontraktsöppning ≤ S): fyllning vid öppningen. Punkter E(mark_open) med q och E efter fyllning;
  inga intrastapelpunkter med positionen.
- Inträde och stop i samma stapel behandlas på samma sätt, med E_after som första punkt efter inträdet.

Exempel O7 (huvud) och O8 (legacy).

## 11. Jämförelsematris

Alla konton: 100 000 startkapital (delkonton andel därav), första öppning 2022-01-01 00:00, terminal 2024-12-31
20:00, samma kontrakts-, mark- och fundingdata, samma kostnad, samma ledger och samma marginalmodell.

| Konto | Signal och riktning | Storlek | Band | Dags-/permanent stopp | ATR-stop | Ombalansering |
|---|---|---|---|---|---|---|
| main | s = medel(7,14,28), long/platt | s × cap | 2 pp | ja / ja | nej | dagsbeslut enligt §7 |
| buy_and_hold | long från första öppning | w = 1 vid första fyllning, fasta enheter | – | nej | nej | aldrig, endast terminal |
| ema_legacy | `ema_adx_trend` 1.0.0 standard (50/200/ADX14/20/ATR14/3), allow_short | ±1 efter kostnad vid inträde (D08), fasta enheter | – | nej | ja, legacy | endast vid signalbyte/stop |
| bb_legacy | `bb_rsi_reversion` 1.0.0 standard (20/2/RSI14/30/ATR14/2), allow_short | som ema_legacy | – | nej | ja, legacy | som ema_legacy |
| old_mix | ema_legacy + bb_legacy, 50 000 vardera | delkonton | – | nej | ja | inga överföringar |
| mom7, mom14, mom28 | en horisont, long/platt | s_h × cap | 2 pp | ja / ja, eget konto | nej | som main |
| no_vol | s = medel(7,14,28) | s × 1 | 2 pp | ja / ja | nej | som main |
| new_mix | mom7 + mom14 + mom28, 1/3 av kapitalet vardera | delkonton | 2 pp per delkonto | per delkonto | nej | inga överföringar eller återställning |

Legacy-semantik som bevaras: beslut vid varje 4H-close, fyllning vid nästa öppning, `hold`-tillståndsmaskinen,
stop = fyllningspris ∓ stopavstånd från signalstapeln, fast under affären, fyllning vid min(öppning, S) för long
(max för short), och efter stop inget nytt inträde i samma riktning förrän signalen ändrats. Vändning long→short vid
samma öppning är ett fill-event med Δq = q_new − q_old. Inga momentumriskstopp läggs på legacy-konton.

Blandningar summeras som faktiska delkonton: E_mix = summan av delkontonas E. Eftersom ledgern är homogen i kapital
(proportionella kostnader, relativa gränser, ingen avrundning) är E_new_mix = (E_mom7 + E_mom14 + E_mom28)/3 för konton
med fullt kapital, och motsvarande för old_mix. Det är en testbar invariant. Motsatta positioner nettas inte.

**Main är inte new_mix.** Main har ett band och ett riskstopp på totalkapitalet; new_mix har tre band på delkontonas
egna vikter och tre risklås. Exempel O9: med cap 0,9 och signaler (1,0,0) har båda ungefär samma enheter, men vid
pris 110 bryter main bandet (vikt 0,3204 mot mål 0,30) medan mom7 inte gör det (0,9083 mot 0,90), och vid ett fall till
97,7 utlöser mom7 sitt dagsstopp (−2,07 %) men inte main (−0,69 %).

## 12. Stresser och körmatris

| Körning | Konton | Scenario | Roll |
|---|---|---|---|
| Normal | alla | A och B | kriterier |
| Kostnad c = 0,0040, hela ledgern omräknad | main | A och B | kriterium C1b |
| Fundingstress: betalda belopp × 2, mottagna oförändrade | main | A | diagnostik |
| Fördröjning +1 stapel | main | A | diagnostik |
| Utan likvidationsmodell | jämförelser | A och B | T-regeln för C3–C5 |

Fördröjning: normal- och riskavsikter fylls en öppning senare med frusen w och priser vid den öppningen. En nyare
normalavsikt ersätter en väntande äldre. Riskavsikter slås ihop med prioriteten i §7; den allvarligaste ligger kvar
tills den fyllts. Terminal fördröjs inte; avsikter som skulle fyllas efter terminal stryks.

## 13. Statistik och beslut

### 13.1 Mått

- Dagsavkastning enligt §4, 1 096 värden, platta dagar inkluderade. Alla värden måste vara ändliga före anrop; en
  icke-ändlig dag ger OGILTIG (ingen tyst borttagning, trots att `stats` annars filtrerar).
- Sharpe = `stats.sharpe` (ddof=1, √365). Newey-West t = `stats.newey_west_t` med lags = 6 (= floor(4 × (1096/100)^(2/9))).
- Nettoavkastning = E_terminal/100 000 − 1. Strikt > 0 krävs.
- Drawdown redovisas med fälten `max_dd_close` och `max_dd_bound` (negativa) samt `_mag` (positiva).

### 13.2 Kriterier (prövas i A och i B)

| # | Villkor |
|---|---|
| C1a | Netto normal > 0 |
| C1b | Netto kostnadsstress > 0 |
| C2 | t ≥ max(2,67, t_krav(N)), N enligt §14.1 |
| C3 | Sharpe(main) > Sharpe(buy_and_hold) |
| C4 | Sharpe(main) > max(ema_legacy, bb_legacy, mom7, mom14, mom28) |
| C5 | Sharpe(main) > Sharpe(old_mix) och > Sharpe(new_mix) |
| C6 | max_dd_close_mag ≤ 0,20 och max_dd_bound_mag ≤ 0,20 och ingen likvidation i main |

Sharpe-jämförelser strikt; t och drawdown inklusive. Alla kriterier sparas som JSON-booleans. Platt kurva ger
0/0/0 och underkänns. Jämförelsevärden enligt T-regeln (§8.4, §9).

Beslut: MORE_RESEARCH endast om körningen är giltig och C1a–C6 är sanna i både A och B; annars REJECT. Det ger bara
underlag för ett separat slutprovsbeslut, aldrig READY_FOR_PAPER eller live.

### 13.3 Giltighet

OGILTIG_DATA: §3/§5-kontroller faller före beräkning. OGILTIG: brott mot någon invariant nedan, upptäckt i körning
eller granskning. Båda sparas med orsak och räknas; inget ekonomiskt beslut. Invarianter: inget köp i lock_day eller
efter permanent stopp; ingen fyllning utanför tillåtna öppningar eller efter terminal; högst ett fill-event per konto
och öppning (plus legacy-stop inom stapel); riskavsikt ökar aldrig |q|; vikt efter köp ≤ cap(D) + 1e−12; varje
funding-händelse bokförd exakt en gång per scenario; inga indata från 2025; storleksidentitet enligt §6.

### 13.4 Redovisning utöver kriterier

Bootstrap av Sharpe (`stats.block_bootstrap_sharpe_ci`, block 20, 2 000, 95 %, seed 0), DSR enligt §14, per halvår
och år, resultat utan bästa året, exponering, omsättning, kostnader, funding (betald/mottagen), riskstopp med tid och
orsak, antal mellanhändelser för funding, T-regelns båda värden och skillnaden A−B.

## 14. Försök, t-krav och DSR

### 14.1 N och t-krav

N = antal olika id i den committade versionen av `research/registry.md` vid registreringscommiten, räknat med
`registry.count_attempts`, inklusive det nya id:t. Vid Codex kontroll fanns 16 id. Om nästa lediga id är H-0017 och
inget annat registrerats blir N = 17 och kravet max(2,67, `stats.t_krav(17)`) = **2,754268270633685**. A2 låser det
faktiska värdet; tidigare trösklar ändras inte.

### 14.2 DSR (diagnostik, inget kriterium)

Beräknas med `stats.deflated_sharpe` på mains dagsavkastning (A, normal kostnad):

| Variant | n_trials | var_trials |
|---|---|---|
| DSR_reg | N från §14.1 | funktionens standard 1/(n−1) |
| DSR_sok | N_sok från §14.3 | 1/(n−1) |
| DSR_reg_var, DSR_sok_var | som ovan | stickprovsvarians (ddof=1) av daglig Sharpe för de tio kurvorna main, buy_and_hold, ema_legacy, bb_legacy, old_mix, mom7, mom14, mom28, no_vol, new_mix |

Beroende: komponenterna och kontrollerna är starkt korrelerade (samma BTC, delvis samma signal). Korrelerade försök
ger ett effektivt antal ≤ det råa antalet, så det råa N_sok är den konservativa ytterkanten. Kontrollkurvorna räknas
inte som försök, eftersom de i förväg är uteslutna som huvudmodell, men de sparas i försöksloggen. Ingen DSR får
beskrivas som sannolikheten för lönsamhet.

### 14.3 Sökhistorik

N_sok räknar varje konfiguration som utvärderats på BTC 2020–2024 eller närliggande data i projektet:

| Källa | Antal |
|---|---|
| Id utan intern sökning: H-0001–H-0008, H-0014, H-0015, H-0016 och det nya id:t | 12 |
| Fas 1 Optuna (H-0009–H-0012): 40 försök × 7 optimeringar × 4 strategier | 1 120 |
| H-0013: möjliga spelböcker | 81 |
| **N_sok** | **1 213** |

Vid A2 räknas tabellen om från registret om fler id tillkommit. Kunskapsläge vid valet: H-0001, H-0005, H-0006
(trendregler) och H-0013:s diagnos var kända; extern litteratur (bland annat Borri m.fl. 2025 med 2025-data) har lästs,
men TraderGO:s skyddade arkiv har inte öppnats. Parametrarna 7/14/28, 60, 10 % och 2 pp har inte sökts fram, men är
inte oberoende av den sedda historiken.

## 15. Sparade data

Fullständiga serier före nedsampling för alla konton och scenarier: varje event med tid, fas
(`start`, `close`, `gap`, `funding`, `after_fill`, `intrabar_high`, `intrabar_low`, `stop_fill`, `liquidation`,
`terminal`), C, q, E, M, P, kostnad, funding, avsikt med beslutstid och orsak, riskstatus och intrastapel-bound.
Kodrevision, dataset-SHA, protokollversion och körnings-id. Avbrott och OGILTIG sparas. En omkörning redovisar orsak och
försöksidentitet.

## 16. Handräknade kontrollfall

Alla med c = 0,0016 och syntetiska priser. Exakta värden i [momentum-a1-orakel.json](momentum-a1-orakel.json);
kontroll med `python3 scripts/momentum-a1-oracles.py --check`.

**O1 avgift, w = 0,5** (Codex orakel). E = 100 000, q_old = 0, P = M = 100. k = −0,16;
q = 0,5 × 100 000/(100 + 0,08) = 499,60032; kostnad = 0,16 × q = 79,93605; E_after = 99 920,06395; vikt 0,5.
Avvikelse mot Codex värden < 1e−13 relativt.

**O2 w = 1 efter avgift.** q = 100 000/100,16 = 998,40256; E_after = 99 840,25559 = q × 100, alltså C = 0 och vikt
exakt 1. Naiva q = 1 000 skulle ge vikt 1,0016.

**O3 basis.** P = 100, M = 99,5, w = 0,5: k = −0,5 − 0,16 = −0,66; q = 50 000/(99,5 + 0,33) = 500,85145;
E_after = 100 000 − 0,66q = 99 669,43804 (basisresultat −250,43, kostnad 80,14); vikt q × 99,5/E_after = 0,5.

**O4 partialköp och partialsälj.** Från O1 (C = 49 960,03, q = 499,60) och pris 110: E = 104 916,07, vikt 0,5238; mål
0,60 ger köp till q = 572,1998 (Δq = 72,60, kostnad 12,78), E_after = 104 903,29. Vid 105: E = 102 042,29, vikt 0,5888;
mål 0,40 ger sälj till q = 388,6150 (kostnad 30,84), E_after = 102 011,45, vikt 0,40.

**O5 funding på samma gräns som handel.** Ränta 0,0001, M = P = 100.
Inträde (0 → 499,60): A betalar 0, E = 99 920,06; B betalar 4,996, E = 99 915,07.
Utgång (499,60 → 0): A betalar 4,996, E = 99 835,13; B betalar 0, E = 99 840,13.
B är gynnsammare vid utgång och A vid inträde; därför prövas båda (D01).

**O6 dagsreset med väntande riskexit.** day_start(D) = 100 000, q = 1 000, C = 50 000. Close 20-stapeln: mark 47,9,
E = 97 900, dag −2,1 % → dagsstopp. Samma close: dagsbeslut s = 1, cap 0,6, vikt 0,4893 → normal köpavsikt, **stryks**
(D07). 00:00: day_start(D+1) = 97 900, lock för D upphör. mark_open 47,5, kontraktsöppning 47,55.
A: funding 4,75, sälj 1 000 till 47,55 (kostnad 76,08), E = 97 469,17 (dag D+1 −0,44 %).
B: sälj först, funding 0, E = 97 473,92. Nästa normalbeslut vid close av D+1, fyllning D+2 00:00.

**O7 mark-high/low-ordning, main.** C = 50 000, q = 500, tidigare peak 105 000. Mark O/H/L/C = 100/112/95/101.
E = 100 000/106 000/97 500/100 500. Bound-peak 106 000 före low: bound-DD −8,02 %. Stängningsserien: −4,29 % mot
105 000. Inget stopp utlöses av bounden.

**O8 legacy-long med ATR-stop.** C = 10 000, q = 900, S = 95. Stop inom stapeln (kontrakt O = 100, L = 93):
E(mark_open 99,9) = 99 910, E(mark_high 101) = 100 900, E(mark_low 92,5, positionen kvar) = 93 250, efter stop vid 95
med kostnad 136,80: 95 363,20. Bound-trough 93 250. Gap (kontrakt O = 94 ≤ S, mark_open 93,9): E = 94 510, fyllning vid
94 med kostnad 135,36 ger 94 464,64 = trough; ingen intrastapelpunkt med positionen.

**O9 main mot new_mix.** cap 0,9, signaler (1,0,0), P = M = 100. main: w = 0,3, q = 299,8561, E_after = 99 952,02.
mom7-delkonto (33 333,33): w = 0,9, q = 299,5686, E_after = 33 285,40. Pris 110: main-vikt 0,3204 → band brutet;
mom7-vikt 0,9083 → hold. Pris 97,7: main −0,69 %, inget dagsstopp; mom7 −2,07 %, dagsstopp.

**O10 första och sista dag.** Start 100 000 vid 2022-01-01 00:00, första beslut från dag 2021-12-31. Terminal
2024-12-31 20:00: C = 60 000, q = 400, mark 95 ger E = 98 000; sälj till kontraktsöppning 95,1 med kostnad 60,864
ger E = 97 979,136. Dagsbeslutet vid 2025-01-01 00:00 skapas inte. 1 096 dagsavkastningar.

**O11 likvidationsgräns.** Legacy-short w = −1 vid P = M = 100: q = −998,40, C = 199 680,51; likvidation vid
mark ≥ 190,48 (mmr 5 %), 199,00 (0,5 %). Main long w = 1: C = 0, tröskel 0 (i float 3e−15); efter 500 betald funding
0,527.

**O12 mål och lika pris.** s = 2/3, vol 60 %: w = 0,1111. C_D = C_(D−h) ger delsignal 0.

## 17. Lösning av M01–M08

| Fynd | Löst i |
|---|---|
| M01 funding/handelsordning | §8.1, §8.4, D01, O5, O6 |
| M02 vikt, avgiftsbas, mättid | §6, §7, D08, O1–O4 |
| M03 intrastapel, mark, marginal | §9, §10, D02–D04, D10, O7, O8, O11 |
| M04 jämförelsematris | §11, D05, D08, D16, O9 |
| M05 första/sista event, midnatt | §4, §7, §8.1, O6, O10 |
| M06 startkapital i drawdown | §10.1 |
| M07 återanvändning av motor | §6–§10: ny ledger krävs; `risk_overlay` och `backtest.run` återanvänds inte för utförande. Rena delar (indikatorer, legacy-signaler, `stats`) får återanvändas oförändrade. |
| M08 N, kontroller, DSR | §14 |

## 18. Kvarstående begränsningar och vad som är verifierat

Verifierat i A1: orakelräkningen i §16 (skriptet, `--check`), t_krav(17) och Newey-West-lags genom `stats`-formlerna,
att mark-datasetets verifieringsfil anger 10 962 staplar och `holdout_loaded = false`.

Endast specificerat, inte verifierat: att data uppfyller §3 för testperioden, antal mellanhändelser för funding, all
motorkod (leverans B–D), resultat.

Modellbegränsningar som gäller även efter godkännande: fast mmr utan trappor eller likvidationsavgift; funding till
mark_open i stället för exakt avräkningsmarkpris; kontinuerliga enheter utan lot/minimibelopp; ingen likviditets- eller
partial fill-modell; noll ränta på outnyttjat kapital; 2022–2024 är redan sedd och kan inte ge ren bekräftelse.

Punkter där Codex uttryckligen bör ta ställning: valet mmr = 5 % som beslutsvärde (D04), den strängare
legacy-bounden (D10) och att både A och B krävs för MORE_RESEARCH (D01). Inga materiella modellval är lämnade öppna i
detta utkast; om Codex underkänner något av dem ska punkten ändras före A2, inte efter ett resultat.
