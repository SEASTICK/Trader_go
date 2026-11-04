# H-0017 C6-01: beslutsunderlag om §10.2-bounden vid likvidation

Datum 2026-11-04. Underlaget har skrivits av Claude för Codex granskning före Edwins beslut, enligt
[C6-uppdraget](claude-uppdrag-momentum-C6.md), avsnittet "Materiell öppen fråga C6-01". Inget alternativ är valt och
ingen semantik för träffstaplar är implementerad. Siffrorna är syntetiska och handräknade i Decimal. Inga
marknadsdata ingår.

## Hänvisningar

- **§10.2:** punkter per stapel med konstant q efter öppningen i ordningen E(mark_open) före fyllning, E_trade, E_post,
  E(mark_high), E(mark_low) och E(mark_close). High räknas före low. Mellanfunding ingår för high med C före betald
  och efter mottagen funding, för low tvärtom. Startkapital och terminalpunkt ingår. Bounden styr inga stopp.
- **§9:** vid träff sätts E till 0 och kontot är platt till terminal. Det beräknade kapitalet före nollställningen
  loggas, även om det var negativt efter ett gap.
- **§13:** C6 = max_dd_close_mag ≤ 0,20 och max_dd_bound_mag ≤ 0,20 och ingen likvidation i main. För övriga konton är
  §10.2 diagnostik.
- **D21:** absorberande nollkonvention, E = C = q = 0 efter likvidation.
- **Edwins C5-01-beslut** ([dokument](momentum-C5-01-edwins-beslut.md)): i en stapel med intrastapelträff bokförs
  ingen mellanhändelse. Alla är olösta, och nollställningen tar kontot efter öppningen. Beslutet låser ledgern och
  marginalunderlaget, inte boundpunkterna.

## Ledger, marginalunderlag och bound

| Serie | Vad den är | Vid intrastapelträff |
|---|---|---|
| Faktisk ledger | kronologisk bokföring | inga mellanhändelser bokförda; C = q = 0 efter nollställning |
| Marginalunderlag (§8.3) | C efter betald och före mottagen funding, vid mark_low | utlöser träffen; loggas med E och MM |
| §10.2-bound | hypotetiska kapitalpunkter med egen peak | **öppen fråga**: vilka punkter, vilken fundingbas och var nollpunkten ligger |

Om denna low-konvention väljs sammanfaller boundens low-punkt (C efter betald och före mottagen funding) med
marginalunderlagets E vid mark_low. Marginalprövningen är oberoende av om bounden har en sådan punkt, och low är ingen
observerad träfftid.

## Syntetiskt sifferexempel

Konto vid stapeln 2023-04-10 08:00 UTC, scenario A, mmr 0,05 och ingen avsikt: C = −600 000, q = 10 000,
avg = 100, föregående close 70 (E = 100 000). Boundens löpande peak före stapeln är 101 000. Det finns ingen samtidig
funding. Mellanevent med M_ref = mark_open = 64: betalning +0,02 kl 08:30 (p = +12 800) och kredit −0,02 kl 10:00
(p = −12 800). C_high = −600 000 + 12 800 = −587 200 och C_low = −600 000 − 12 800 = −612 800.

| Fall | Mark O/H/L/C | E_open = E_trade = E_post | E_high | E_low (= marginalunderlag) | MM vid low | Träff |
|---|---|---|---|---|---|---|
| 1, positivt E_low | 64 / 66 / 63,5 / 65 | 40 000 | 72 800 | 22 200 | 31 750 | ja, inom stapeln |
| 2, negativt E_low | 64 / 66 / 58 / 60 | 40 000 | 72 800 | −32 800 | 29 000 | ja, inom stapeln |
| 3, gap | O = 55 | E_open = −50 000 (MM 27 500) | – | – | – | ja, vid gappunkten |

Vid mmr 0,005 träffas inte fall 1 (MM 3 175). Då gäller vanlig §10.2 utan träff, med de två mellaneventen bokförda
kronologiskt.

## Möjliga punktsekvenser (konsekvensillustrationer, inga nya scenarier)

**A. High/low med olöst hypotetisk funding och oklippta negativa värden, sedan nollpunkt (ett förslag till tillägg; §10.2 låser inte fortsättningen vid likvidation).** Open räknas på ingående C/q före A-funding och fyllning.
Trade och post är öppningens kapitalfaser, och high och low räknas med q_open och de olösta mellaneventen som
hypotetiska belopp. Negativa värden står kvar oklippta. Därefter kommer en nollpunkt
`liquidation` (E = 0) och nollor till terminal. Vid gapträff ingår E_open, även negativt, och sedan nollpunkten. Det
blir inga high/low-punkter med positionen.
**B. Som A, men ingen punkt under 0.** Negativt kapital före nollställningen syns i marginal- och gapspåret men inte i
bounden. Trough blir 0.
**C. Inga high/low-punkter i träffstapeln.** Punkterna open (ingående C/q), trade och post följs av nollpunkten. Vid
gap gäller samma som B.

| Fall | A: punkter (peak 101 000) | A: max_dd_bound | B | C |
|---|---|---|---|---|
| 1 | 40 000, 40 000, 40 000, 72 800, 22 200, 0 | −1 | −1 | −1 |
| 2 | 40 000, 40 000, 40 000, 72 800, −32 800, 0 | −1,3247524752475248 | −1 | −1 |
| 3 | −50 000, 0 | −1,4950495049504950 | −1 | −1 |

High kan inte höja peak i dessa fall. En högre peak ändrar bara A:s negativa fall, eftersom 0/peak − 1 = −1 för alla
peak > 0. Efter nollpunkten är alla punkter 0, så ingen senare punkt ändrar måttet. Ingen variant räknar 0/0, eftersom
boundens peak är minst 100 000.

## Konsekvens

- **Huvudmodellen:** varje likvidation gör C6 falskt genom likvidationsvillkoret i §13.2. Alla varianter ger ett
  lokalt bidrag med magnitud ≥ 1 > 0,20. För en giltig main-körning med oförändrad ledger, marginalflagga och
  close-serie kan valet därför inte ändra C6 eller den ekonomiska klassificeringen REJECT/MORE_RESEARCH. OGILTIG och
  OGILTIG_DATA är separata frågor. Valet ändrar den redovisade magnituden: lokalt bidrag över 1 i A vid negativt
  kapital före nollställning, annars lokalt exakt 1. Hela förloppets mått är min(tidigare minimum, lokalt minimum)
  och kan alltså redan vara lägre.
- **Övriga konton (diagnostik):** samma skillnad i redovisad magnitud, utan beslutseffekt.
- **Handel:** ingen variant matar stopp, avsikter eller marginalbeslut.

## Vad som kräver Edwin

1. Ska de olösta mellaneventen i en träffstapel användas som hypotetiska belopp i C_high/C_low (A och B), eller ska
   high/low utelämnas i träffstapeln (C)?
2. Ska negativt kapital före nollställningen (E_low eller gapkapital) ingå oklippt i bounden (A), eller ska bounden
   inte gå under 0 (B/C)?
3. Nollpunkten läggs direkt efter den sista punkten med positionen i träffstapeln: efter low i A/B, efter E_post i C
   och efter E_open vid gap. Därefter gäller E = 0 till terminal, utan punkter med positionen. Ingen ordning mellan
   träffen och fundingtiderna påstås i någon variant.

Ingen ändring av det frysta protokollet eller av C5-01-beslutet. Det valda alternativet dokumenteras som ett tillägg
med länk hit.

## Rättning efter Codex granskning

Codex granskade underlaget i [momentum-C6-01-granskning-underlag.md](momentum-C6-01-granskning-underlag.md) och
bedömde att det behövde rättas. Rättningarna:

- **A är ett förslag till tillägg.** Rubriken ovan är ändrad, så att A inte framstår som entydigt ur §10.2.
- **B var inget färdigt punktkontrakt.** B kan betyda att negativa punkter utelämnas eller att de ersätts med 0.
- **C kopplade ihop två oberoende val.** Utelämnade high/low och behandlingen av negativt gapvärde är separata
  frågor.
- **Ett fundingalternativ saknades:** high/low med q_open men utan olöst funding (C_post). Det ger high 60 000 och
  low 35 000 respektive −20 000.
- **Fall 3 är ett separat gapfall.** Eventuella mellanevent där har M_ref 55 och absorberas.
- **Historikförbehåll:** tabellens värden är lokala bidrag. Hela förloppets mått är min(tidigare minimum, lokalt
  minimum).
- **Konservativitet vid negativt kapital:** en högre peak gör en negativ trough mindre negativ. A är därför inte
  bevisat strängast under −100 %.
- **Rätt beslutsnamn:** REJECT/MORE_RESEARCH, inte REJECT/PASS.

Codex ersatte frågorna 1–3 ovan med fyra valfrågor (H, I, G och P). Edwins svar finns i
[momentum-C6-01-edwins-beslut.md](momentum-C6-01-edwins-beslut.md).

## Kompletterande exempel (andra rättningen efter Codex granskning av beslutet)

Codex [granskning av det dokumenterade beslutet](momentum-C6-01-granskning-beslut.md) krävde exempel där high höjer
peak och där ett tidigare minimum styr. Exemplen följer Edwins val (H1, I1, G1, P1) och är handräknade i Decimal.
Alla tal är syntetiska.

**Fall 4, high höjer peak före en negativ low.** Scenario A, mmr 0,05, ingen avsikt och ingen samtidig funding.
C = −300 000, q = 4 000, boundens peak före stapeln 100 000 och tidigare minimum −0,05. Mark O/H/L = 100/110/70.
Mellanevent med M_ref 100: betalning +0,01 (p = +4 000) och kredit −0,01 (p = −4 000). Gapmarginal: E_open 100 000 >
MM 20 000, ingen gapträff. C_high = −296 000 och C_low = −304 000. Marginalunderlaget vid low ger E −24 000 ≤ MM
14 000, alltså träff inom stapeln.

| Punkt | E | Peak efter punkten | Drawdown | Ackumulerat minimum |
|---|---|---|---|---|
| open | 100 000 | 100 000 | 0 | −0,05 |
| trade | 100 000 | 100 000 | 0 | −0,05 |
| post | 100 000 | 100 000 | 0 | −0,05 |
| high | 144 000 | 144 000 | 0 | −0,05 |
| low | −24 000 | 144 000 | −7/6 ≈ −1,1666666666666667 | −7/6 |
| liquidation | 0 | 144 000 | −1 | −7/6 |

Med peak kvar på 100 000 hade low gett −1,24. Den högre peaken gör alltså den negativa troughen mindre negativ, vilket
illustrerar reservationen om konservativitet.

**Fall 5, ett tidigare minimum styr (ordnade punkter).** Boundens peak börjar på 100 000. Stapel 1 och 2 har ingen
träff, och stapel 3 likvideras inom stapeln. Kapitalpunkterna är syntetiska och valda så att kvoterna blir exakta:

| Stapel | Punkt | E | Peak | Drawdown | Ackumulerat minimum |
|---|---|---|---|---|---|
| 1 | open | 100 000 | 100 000 | 0 | 0 |
| 1 | trade | 100 000 | 100 000 | 0 | 0 |
| 1 | post | 100 000 | 100 000 | 0 | 0 |
| 1 | high | 110 000 | 110 000 | 0 | 0 |
| 1 | low | 66 000 | 110 000 | -0.4 | -0.4 |
| 1 | close | 90 000 | 110 000 | -0.1818181818 | -0.4 |
| 2 | open | 90 000 | 110 000 | -0.1818181818 | -0.4 |
| 2 | trade | 90 000 | 110 000 | -0.1818181818 | -0.4 |
| 2 | post | 90 000 | 110 000 | -0.1818181818 | -0.4 |
| 2 | high | 100 000 | 110 000 | -0.0909090909 | -0.4 |
| 2 | low | 82 500 | 110 000 | -0.25 | -0.4 |
| 2 | close | 95 000 | 110 000 | -0.1363636364 | -0.4 |
| 3 | open | 95 000 | 110 000 | -0.1363636364 | -0.4 |
| 3 | trade | 95 000 | 110 000 | -0.1363636364 | -0.4 |
| 3 | post | 95 000 | 110 000 | -0.1363636364 | -0.4 |
| 3 | high | 100 000 | 110 000 | -0.0909090909 | -0.4 |
| 3 | low | 30 000 | 110 000 | -0.7272727273 | -0.7272727273 |
| 3 | liquidation | 0 | 110 000 | -1 | -1 |

Lokala minima: stapel 1 −0,4 (low 66 000 mot peak 110 000), stapel 2 −0,25 (low 82 500 mot samma peak) och stapel 3
−1. Efter stapel 2 är det ackumulerade minimumet fortfarande −0,4: det tidigare minimumet styr. Efter stapel 3 är det
−1. Peak 110 000 behålls genom likvidationen.

**Var negativa punkter kan uppstå.** Utan träff är E_low > MM ≥ 0 och E_open > MM ≥ 0, så alla punkter med position
är positiva. Negativa boundpunkter uppstår bara i själva likvidationsstapeln (I1/G1), och därefter är alla punkter 0.
