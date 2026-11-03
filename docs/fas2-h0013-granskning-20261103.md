# H-0013 – verklig serverkörning och resultatgranskning, 2026-11-03

**Beslut: REJECT. Alla fem förregistrerade krav faller.** H-0013 avslutas enligt protokollet utan slutprov. Ingen strategi godkänns för papper eller live. Den tekniska app–kö–worker–resultatkedjan är verifierad; Fas 2 som leverans är inte helt klar eftersom release och slutgodkännande återstår.

## Identitet, körning och källa

- Edwin gav uttryckligt ja efter förkontrollen i docs/fas2-h0013-forkontroll-20261103.md. Köning från installerad Mac-app **9471e51**, tvåstegsförberedelse, en enda köning.
- Körnings-id **ca59d441-3ab3-489b-b762-c368a6220834**, registered, h0013_adaptive_playbook, h0013-evaluation/1.0.0.
- Skapad **14:26:26,184374 UTC**, workerstart **14:26:29,305311**, publicerad **14:35:05,340088**. **516,035 sekunder**, cirka 8 minuter 36 sekunder, försök **1 av 3**, progress=1, error=null.
- Workerrevision **b44d3cecaac6e05077c8ce2c74acf73a8455d0d8**, källa TRADERGO_REVISION.
- Original: `/var/lib/tradergo/h0013-attempts/H-0013-20261103T143504962276Z-completed.json`.
- Byteidentisk arkiverad kopia: [resultatfil](../research/results/H-0013-20261103T143504962276Z-completed.json), **588242 byte**, SHA-256 **f752202e7c6413265d0dc404f546720d835d569af2251704134a41b44d561ee1**.
- Exakt **en** run_results-rad. Dess payload, stats och curves jämfördes med originalfilen och är identiska. Kanonisk JSON-SHA-256 **7a9e582fb0703ca3dfd9aeea7c6cc53c8c27ec3e70d28f99be8499c16f44b87e**.
- Tio utvärderingssteg done, 200 fullständiga permutationer och 81 spelböcker. Inga reducerade testinställningar.

## Data och gränser

Dataset **6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c**, samma 120 frysta arkiv som före körningen. Manifest SHA-256 **9401fa4210b8859f17476eaee5211d66814ef74fc508ea51f63f75387e14675f**.

Den framgångsrika workerkörningen verifierade även inlästa staplar/funding mot manifestets separata hashkontroller. Resultatet redovisar **10962 staplar**, **5481 fundinghändelser**, 2020-01-01 00:00 till 2024-12-31 20:00 UTC och inläst datafingeravtryck **4d5cfd5f564a9b64d0538246dfea0d36d60b5e9de0e4631b9251f8a64823d250**. `holdout_loaded=false`.

Bedömningen gäller sex testfönster 2022–2024, **6570 staplar och 1096 dagar**. Sex sista staplar utelämnas enligt den förregistrerade implementationstolkningens fönsterslut. Jämförelserna har exakt samma staplar och fönsterkonventioner. Köp-och-behåll här är därför inte en obruten femårsinvestering och ska inte jämföras direkt med andra experiment utan dessa konventioner.

## Omräknade kriterier

| Krav | Sparat värde och oberoende kontroll | Utfall |
|---|---|---|
| t ≥ 2,67 | **−1,8023331649** | Faller |
| Netto med 2,5× kostnader > 0 | **−13,0112149771 %** | Faller |
| Sharpe > köp-och-behåll | **−0,7675151113** mot **0,5018238409** | Faller |
| Sharpe > bästa ensamma kandidat | **−0,7675151113** mot EMA **0,2735421859** | Faller |
| Sharpe > likaviktad blandning | **−0,7675151113** mot **−0,1821711632** | Faller |

Alla booleska kriterier och REJECT är omräknade från resultatet. Protokollets låsta t-krav 2,67 avgör; dagens 15 hypoteser ger 2,7131 som redovisas men inte används för att ändra det förregistrerade beslutet.

Netto **−10,8641844378 %**, maximal drawdown **−11,4721392441 %**, Sharpe 95 % block-bootstrap **−1,3628 till −0,2408**. Fem affärer, fyra stop-utgångar, inga likvidationer. Kostnader 1,5243 % och betald funding 0,1381 % av startkapitalet. Alla affärer i första halvåret 2024; övriga fem testfönster platta. Den slutliga spelboken är platt i alla fyra lägen.

Permutation: **175/200** minst lika hög Sharpe, p=**0,875**, plus-en-estimat 0,8756219. Deflated Sharpe med 81 försök: standard **7,5304e−7**, spelboksvarians **5,7750e−8**. Slumpkontroll t **−0,129588**. Utan bästa året: Sharpe **−0,939961**. Inget av detta stödjer en verifierad kant.

## Reproducerbar granskning utan ny forskningskörning

Kör från reporoten:

```sh
engine/.venv/bin/python research/audits/h0013-20261103/review.py
```

[Sparad verifiering](../research/audits/h0013-20261103/verification.json). Skriptet importerar inte traderlab och kör inga strategier. Det läser endast den arkiverade resultatfilen och räknar om avkastning, dags-Sharpe, Newey-West med Bartlett-vikter, maximal drawdown, de fem kriterierna och permutationsandelen. Det kontrollerar sex fönster, 200 permutationer, 81 spelböcker, kurvlängder och jämförelsernas slutvärden samt skalade kostnader/funding per fönster.

De fem affärernas procenttal har kapital vid respektive inträde som nämnare. Min första summeringskontroll var därför felaktig; korrekt avstämning med ränta på ränta ger exakt kurvans −10,864184 %. Detta var ett fel i granskningsprovet, inte i motorn. De fullständiga individuella affärsbeloppen lagras inte i payload; någon separat omräkning av varje fundinghändelse/stoppris eller fullständiga jämförelseseriers binära SHA har inte påståtts här. Dessa bygger på tidigare kodgranskning och arkiv-/datakontroller.

## Installerad app och drift

- Research Lab visar **Klar, 100 %, 1 av 3**, HISTORIK och REJECT; inga SIM-siffror används.
- Appens faktiska `readResult` kördes separat på originalfilen via TypeScript-transpilering: ok=true, missing=[], tradeIssues=[], sex fönster, sex kurvor inklusive huvudkurvan och fem affärer.
- Native AX visar kriterier, osäkerhet, jämförelser, marknadslägen, fönsterval, affärslogg och spårbarhet. Visuellt kontrollerades beslutet, jämförelsetabellen, huvudkurva/drawdown och byte från köp-och-behåll till Bollinger/RSI. Ingen ny ljus-temakontroll av detta verkliga resultat; A2:s temakontroll är separat.
- 1500 jämförelsepunkter på samma urval av 6570 staplar, ändliga värden och slutvärden som stämmer med nyckeltalen. H-0013:s jämförelsekurva stämmer med huvudkurvan vid samma tidpunkter.
- `check-single-worker.sh` PASS: PID **30868**, b44d3ce, taget lås, paket verifierat, **0 omstarter**. Efteråt tom slot, ingen queued/running och exakt en H-0013-körning.
- Journalen visar `result_accepted=True`, 0 WARNING/ERROR under H-0013. Tjänstens kumulativa MemoryPeak **118521856 byte** sedan tjänstestart; inte en isolerad mätning av enbart H-0013. CPU-stickprov på beräkningsprocessen visade ungefär en kärna och cirka 91 MB RSS.
- Kön skrev inte registrets beslut: Supabase hypotheses.decision var fortsatt null vid efterkontroll. Ett nytt Git-registerbeslut läggs till separat efter denna granskning. Den driftsatta katalogspegeln följer fortfarande sitt paketerade register, inte senare Git-commits.

## Register- och exportkontroller

De riktade testerna `test_registry_and_experiment.py`, `test_registered_export.py` och `test_catalog.py` passerar med den nya resultatfilen. Fas 1-exporten och det äldre resultatformatets utdata är oförändrade.

## Begränsningar och nästa kontroll

Endast BTC, samma redan använda utvecklingshistorik, få affärer och en enda aktiv testepisod. Permutationsnollmodellen är förregistrerad men icke-kausal. Fönsterstarterna är platta och sluten stängs i förtid enligt dokumenterade tolkningar. Kontrakts-OHLC används, inte separat mark-price; 1× är ingen komplett modell av verklig terminsdrift. Ingen andra börskälla eller ny realtidsperiod har verifierats.

**Resultatet kan användas för det förregistrerade REJECT-beslutet. Det är inte stöd för papper eller live.** H-0013 går inte vidare till slutprov. Nästa leveranskontroll är release/testkanal, installerad Stable och slutligt Fas 2-godkännande. Förändrad urvalsregel eller nya kandidater kräver en ny registrerad hypotes; H-0013 anpassas inte efter detta resultat.
