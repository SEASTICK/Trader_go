# H-0013: tolkningar för utvärdering, kontroller och beslut

Skrivet 2026-11-02, innan arbetsområde 5 implementerades och innan något körts på riktig data.
`research/fas2-protokoll.md` ändras inte. Protokollets avsnitt "Beslutskriterier" och "Kontroller som rapporteras"
säger vad som ska mätas men inte alltid exakt hur. Här står varje sådan fråga och den tolkning koden använder.
Fönsterkonventionerna i `docs/fas2-walkforward-tolkningar.md` gäller oförändrade.

## Samma observationsperiod och samma exekvering

| # | Fråga | Tolkning | Varför |
|---|---|---|---|
| U1 | Vad betyder "samma period och samma kostnader" för jämförelserna? | Varje jämförelse körs genom samma sex testfönster och samma fönsterkonventioner som H-0013. Det ger exakt samma staplar med avkastning och samma dagar. | Codex granskning av PR #71: jämförelserna ska använda samma underliggande observationsperiod och uttalade exekveringsantaganden. Utan det skulle skillnaden delvis bero på periodgränser i stället för strategi. |
| U2 | Vilka fönsterkonventioner gäller för jämförelserna? | Platt före fönstret, första fyllning tidigast vid andra öppningen i fönstret (beslut vid första stapelns stängning, som H-0013), stängning senast vid näst sista öppningen och samma kapitalbas vid ihopsättning. | Samma som H-0013 (punkt 7–9). H-0013 kan inte fylla vid fönstrets första öppning, eftersom spelboksbytet sker där. |
| U3 | Köp-och-behåll? | Long 1× på samma terminer från första tillåtna fyllning till stängningen i varje fönster, med kostnader och finansieringsränta. | Protokollet: "på samma terminer och period (med kostnader och finansieringsränta)". |
| U4 | Ensam kandidat? | Kandidatens egen målposition med standardparametrar, long och short, utan lägesfilter och utan krav på ny signal. Kandidatens ATR-stop gäller. | Protokollet: "long och short som strategin själv avgör, utan lägesfilter". Kravet på ny signal är en handelsregel för spelboken, inte för kandidaten. |
| U5 | Likaviktad blandning? | Hälften av kapitalet i varje ensam kandidat från 2022-01-01. Kurvan är medelvärdet av de två ihopsatta kurvorna, och varje halva växer för sig utan ombalansering. Sharpe räknas på dagsavkastningen för den kurvan. | Ordagrant protokollet. Vid fönstergränserna är båda halvorna platta, så ingen ombalansering behövs. |
| U6 | Riskfilter? | `ema_adx_trend` ensam (U4), men platt när läget för nästa stapel är `ned/hög vol`. Läget räknas på samma sätt som i spelboken. | Protokollet. Bara rapport. |

## Kriterier

| # | Fråga | Tolkning | Varför |
|---|---|---|---|
| U7 | Vilket t-krav? | Det registrerade **2,67** (N = 13). Kravet för dagens N i registret (`stats.t_krav`) redovisas bredvid, men avgör inte. | Protokollet anger 2,67 vid registreringen, och kriterier ändras inte i efterhand. H-0014 och H-0015 registrerades senare och höjer N, så en avvikelse mellan värdena syns i resultatet. |
| U8 | Sharpe och t? | `stats.sharpe` (365) och `stats.newey_west_t` på dagsavkastningen (`stats.daily_returns`) av den ihopsatta kurvan. Samma mått används för alla jämförelser. | Som Fas 1. |
| U9 | Kostnadsstress? | Samma spelbok per fönster som i normalkörningen (vald med normala kostnader), men prövad med 2,5 gånger avgift, spread och slippage. Finansieringsränta som vanligt. Kriterium 2 är slutkapital minus 1 > 0. | Som Fas 1:s `_stitch`. Ett nytt urval med stressade kostnader vore en annan körning. |
| U10 | Beslut? | `MORE_RESEARCH` bara om alla fem är sanna, annars `REJECT`. Ett mått som inte kan räknas (till exempel t utan spridning) räknas som falskt. | Protokollet. Fail closed. |
| U11 | Riskmodell? | 1× utan hävstång, kandidatens ATR-stop och backtestmotorns likvidation och finansieringsränta. Likvidationer, stop-utgångar, exponering och total finansieringsränta redovisas. | Protokollet: 1×, finansieringsränta. Mark-price och likvidationsprecision verifieras inte i Fas 2 (känd svaghet). |

## Kontroller som rapporteras

| # | Fråga | Tolkning | Varför |
|---|---|---|---|
| U12 | Hur slumpas lägen i permutationstestet? | Det gällande dagsläget (efter hysteres) för hela utvecklingsperioden permuteras: dagar med känt läge byter etikett med varandra, och varje dag flyttas som ett block. Dagar med `okänt` ligger kvar. Samma permuterade serie används i varje träning och test. Frö 0, 200 permutationer, `numpy.random.default_rng`. | Protokollet: blockvis per dygn, hela walk-forward inklusive urvalet körs om. Att behålla `okänt` på plats bevarar uppvärmningen, som inte är en lägesetikett. |
| U13 | p-värde? | Andelen permutationer med Sharpe utanför urvalet ≥ H-0013:s, alltså k/200. Antalet k redovisas också, och (k+1)/(201) som kontroll. Varje permutations Sharpe och spelböcker sparas. | Protokollets definition. Bara rapport. |
| U14 | Deflated Sharpe med 81 försök? | `stats.deflated_sharpe(dagsavkastning, 81)` med standardvariansen. Dessutom redovisas varje fast spelboks Sharpe utanför urvalet (alla 81 genom samma fönster, utan urval). Deflated Sharpe räknas också med variansen mellan dem, omräknad till Sharpe per dag. | Protokollet anger 81 försök. Variansen mellan försöken är okänd utan de 81 körningarna, och båda varianterna redovisas. |
| U15 | Osäkerhet? | Block-bootstrap av Sharpe (block 20 dagar, 2000 dragningar, frö 0, 95 %) med `stats.block_bootstrap_sharpe_ci`. | Som tidigare hypoteser. |
| U16 | Resultat utan bästa året? | Avkastning per kalenderår (2022, 2023, 2024) av den ihopsatta kurvan. Utan bästa året: dagarna i året med högst avkastning tas bort, och avkastning och Sharpe räknas på resten. | Protokollet. |
| U17 | Regimresultat? | Dagar, affärer, avkastning och Sharpe per läge utanför urvalet. Varje dag hör till läget som styr dess staplar (punkt 2), och affären hör till läget vid fyllningen (punkt 3). | Som walk-forward. |
| U18 | Slumpkontroll? | `experiment.random_label_control` på staplarna från 2022-01-01 till 2025-01-01 exklusivt (frö 0). | Som tidigare hypoteser. |

## Spara alla försök

| # | Fråga | Tolkning | Varför |
|---|---|---|---|
| U19 | Vad sparas? | Varje körning skriver en ny fil i `research/results/` som aldrig skriver över en annan. Den skrivs även när körningen avbryts eller misslyckas, då med status `aborted`, felet och allt som hann räknas. Status är `completed`, `aborted` eller `invalid`. Beslut skrivs bara för `completed`. | CLAUDE.md regel 2 och protokollet: misslyckade försök tas aldrig bort och räknas. |
| U20 | Registrering? | Körningen vägrar starta om H-0013 inte finns i den committade versionen av `research/registry.md`. Commit och kontrakts- och walk-forward-versioner sparas i resultatet. | Registerregeln. |

Granskaren avgör om tolkningarna godtas innan någon riktig körning görs.
