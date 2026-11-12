# Rullning B: kandidattidtabell för en möjlig H-0023 (låst före mätning)

Skrivet 2026-11-12, **före** någon volym- eller datatäckningsmätning av tidtabellen. Det här dokumentet låser exakt en kandidat och dess beslutsregel. **Ingen H-0023 är registrerad**, ingen basis, avkastning, t-statistik eller beta beräknas, och inga arkiv från 2025-01-01 eller senare öppnas. Dokumentet ändras inte efter att mätningen gjorts: en annan tidtabell vore en ny kandidat.

## Varför den här idén (öppen redovisning)

Idén valdes **efter** att H-0022:s datatäckningsgranskning (#119) visat att likviditeten i den inrullade serien var för låg: vid utträdet sju dagar före förfall var nästa serie den näst närmaste, och dess 20-dagarsmedianvolym räckte bara för minst fyra mynt i 9 av 13 cykler, mot kravet 10. Kandidaten är alltså formad av en volymdiagnos (volym, inte avkastning), och det måste stå i en eventuell H-0023-rad. Ingen parameter har valts utifrån avkastning, för ingen avkastning har räknats.

## Kandidaten (en enda)

Samma universum, kostnader, kassabok och riskstopp som H-0022. Skillnaden är **när** man går in och **vilken serie** som väljs:

* **Serie per cykel:** den kvartalsserie vars förfall är **närmast efter föregående kontrakts förfall**, alltså `E_k` när föregående förfall var `E_{k-1}`. Efter `E_{k-1}` är det den närmaste serien (den som tidigare var näst närmast). Är den inte annonserad och handlad enligt `universe_at` på beslutsdagen blir cykeln **platt**; ingen annan serie ersätter den (0924-serien 2021 saknar daterad annons och blir platt, som i H-0022).
* **Beslutsdag `D_k`:** förfallsdagen `E_{k-1}` (fredag, förfall 08:00 UTC). Beslutet fattas på dagens **sista avslutade dagsstapel**, det vill säga stapeln för `E_{k-1}`, som är färdig vid 00:00 UTC dagen efter. Allt urvalsunderlag (annons, verifierad handel, 20 dagars volym, kontraktsstorlek, spot) använder bara data till och med `D_k`.
* **Inträde:** fyllning vid **nästa 00:00 UTC**, `F_k = D_k + 1 dag` (lördag), `open` i den dagens 1d-stapel för terminen (last price) och spot.
* **Utträde:** som i H-0022, **sju kalenderdagar före serien förfall**: `X_k = E_k − 7` vid 00:00 UTC, `open` i den dagens 1d-stapel för båda benen. Mellan `X_{k-1}` och `F_k` ligger portföljen i kontanter (cirka åtta dagar) utan ränta.
* **Första cykeln:** `D_1 = 2021-03-26` (de fyra försvunna underliggandes sista förfall, första dag utan efterhandsurval), vilket är samma cykel 1 som i H-0022. **Sista cykeln:** förfall 2024-09-27, beslutsdag 2024-06-28, alla beslutsdagar inom det biasfria fönstret 2021-03-26 till 2024-08-13 (SOL lanserades 2024-08-14 och saknas, som i H-0022).
* **Oförändrat från H-0022 (inga nya parametrar):** de sju mynten, kontraktsstorlek 10 USD, likviditetstak 2 % av medianvolymen över de senaste 20 handelsdagarna till och med beslutsdagen (volym i kontrakt × 10 USD), minsta position 10 000 USD, startstorlek 20 000 USD (140 000 / 7), kostnader 50 bp och 125 bp i stress, markprisbaserat riskstopp, datakraven.

Cykelkalendern genereras ur universumtabellen och `universe_at` utan priser: `research/universe/rullning-b-rapport.md` och `research/coverage/rullning-b-datatackning.json`.

## Vad som mäts (endast täckning, inga priser i något beslut)

För varje mynt och cykel, med exakt de kontroller som `h0022_coverage.audit_coin_cycle` använder (efter PR #119):

1. Valbar på beslutsdagen enligt `universe_at`, verifierad stapel med volym på beslutsdagen (termin och spot), minst 20 handelsdagar före den, kontraktsstorlek 9,5–10,5.
2. Exakt gemensam `open_time` 00:00:00 UTC för båda benen på fyllnings- och utträdesdagen, volym > 0 på fyllningarna, markpris varje hållen dag, nästa öppning för både termin och spot efter varje hållen dag.
3. Likviditet: 20-dagarsmedianen mot 500 000 USD (minsta position 10 000 USD) och mot 1 000 000 USD (startposition 20 000 USD).
4. Arkiv: alla använda filer verifieras mot sparad checksumma; luckfyllnad bara med verifierade dagsfiler (2023-08, manifest i repot).

## Beslutsregel (låst nu)

* **Ja, möjlig giltig täckning:** vid **minsta position 10 000 USD** (den mest tillåtande gränsen) når tidtabellen minst **46 av 91** mynt-cykler **och** minst **10 av 13** cykler med minst **4** handlade mynt, och **0** mynt-cykler blir `OGILTIG` på grund av saknade staplar. Då är täckningen ett nödvändigt, inte tillräckligt, villkor: faktiska positioner beror på kassabokens värde, så startstorlekens siffror redovisas som information.
* **Nej:** annars. Då stannar arbetet där och inget nytt tröskelvärde, ingen ny storlek och ingen ny tidtabell föreslås i samma PR.

Ingen H-0023-rad skrivs oavsett utfall.
