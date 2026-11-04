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

**A. High/low med olöst hypotetisk funding och oklippta negativa värden, sedan nollpunkt (ett förslag till tillägg; §10.2 låser inte fortsättningen vid likvidation).** Punkterna open, trade, post, high och low räknas med q_open och de
olösta mellaneventen som hypotetiska belopp. Negativa värden står kvar oklippta. Därefter kommer en nollpunkt
`liquidation` (E = 0) och nollor till terminal. Vid gapträff ingår E_open, även negativt, och sedan nollpunkten. Det
blir inga high/low-punkter med positionen.
**B. Som A, men ingen punkt under 0.** Negativt kapital före nollställningen syns i marginal- och gapspåret men inte i
bounden. Trough blir 0.
**C. Inga high/low-punkter i träffstapeln.** Punkterna open, trade och post räknas med q_open, sedan nollpunkten. Vid
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

- **Huvudmodellen:** varje likvidation gör C6 falskt genom likvidationsvillkoret i §13. Alla tre varianterna ger
  magnitud ≥ 1 > 0,20. Valet kan därför inte ändra C6, REJECT/PASS eller något beslut för huvudmodellen. Det ändrar
  bara den redovisade magnituden vid negativt kapital före nollställning (A: över 1, B/C: exakt 1).
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
