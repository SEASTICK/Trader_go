# Granskning av inledande Fas 2 och tvärsnitt, 2026-11-02

Granskad main: 785fd8f. Ingen kod ändrad i nya strategier eller frysta resultat.

## H-0013: implementationen saknas i granskad commit

`research/fas2-protokoll.md` och registreringen finns. Däremot finns inga committade källfiler för `regime`, `adaptive` eller `fas2`, inga motsvarande källkodstester och ingen H-0013-ingång i worker/RPC/UI. Kvarvarande pycache-filer är inte granskningsbar källkod. Motor, tidsgränser och faktisk integration kan därför inte godkännas. Fråga Claude efter gren, commit/PR och opushade filer.

Protokollet beskriver en ny sammansatt forskningshypotes som använder två tidigare REJECT-strategier. Det är inte en färdig driftmotor som väljer mellan godkända strategier. Kandidaternas beslut får inte uppgraderas genom att de ingår i H-0013; eventuellt godkännande gäller en ny fryst kombination efter dess egna kontroller. Protokollet redovisar redan att utvecklingsperioden och regimresultaten är sedda.

## Fynd i det separata tvärsnittsarbetet H-0014/H-0015

Dessa moduler är multi-market-forskning, inte H-0013:s adaptiva motor. Resultaten är fortsatt REJECT. De ingår inte i Stable 0.1.19 (byggd från 37a3baf).

1. **P1 – nyttan av skyddat slutprov kan förloras innan filtrering.** `engine/traderlab/xsrun.py:33`, `:41` och BTC-läsningen i `run` anropar arkivläsarna utan `start`/`end`. Filtrering sker först efter att alla lokala arkiv lästs. Om 2025-arkiv finns öppnas de trots protokollets löfte. Befintliga läsare stödjer redan begränsade arkivurval. Testet som returnerar data till 2026 verifierar bara slutresultatets datum, inte vilka arkiv som öppnas. Nästa kontroll: förbjud öppning av arkiv från slutprovet i ett test och skicka periodgränser till samtliga läsare.

2. **P1 – portföljen kan överleva negativt kapital.** `engine/traderlab/portfolio.py:85–92` håller kvar positioner utan marginal-/likvidationsmodell och utan absorberande konkursläge. Syntetiskt verifierat: öppningar `[100,100,400,100]`, shortvikt −1, noll kostnad ger kapital `[1,-2,1]`. Kontot återuppstår efter −200 % kapital. En bruttoexponering på 1× vid ombalansering löser inte detta. Nästa kontroll: oberoende marginalmodell, extrema short-rörelser och terminalt insolvensläge före nya resultat; ändra inte gamla frysta körningar i efterhand.

3. **P1 – saknad funding blir gratis funding.** `engine/traderlab/xsrun.py:40–44` ersätter saknad finansieringsdata med tom serie. `portfolio.funding_per_day` behandlar den sedan som noll. H-0015 kan ranka på ett tillgängligt delurval och båda körningarna kan debitera fel kostnad utan ett datakvalitetsfel. Luckor, dubbletter och fullständiga avräkningar valideras inte där. Nästa kontroll: avbryt ofullständiga forskningsdataset, redovisa täckning per instrument och spara checksummebaserat dataset-id.

4. **P2 – avnotering använder en exekvering som inte var känd vid sista öppningen.** `engine/traderlab/portfolio.py:75–86` nollställer rörelsen när nästa öppning saknas och stänger på senaste kända öppning. Det innebär en retroaktiv fyllning innan frånvaron blivit känd; ett datafel behandlas dessutom likadant som en dokumenterad avnotering. Nästa kontroll: tidsstämplade tillgängliga avnoteringsbesked/settlement och fail-closed för oförklarade luckor. Historiska perioder får inte förkastas utifrån framtida datakvalitet och sedan kallas neutrala urval.

## Utförda kontroller

- Tio befintliga portfölj-/xsrun-tester passerar. Dessa täcker inte felen ovan.
- Det deterministiska konkursprovet reproducerar negativt kapital följt av återhämtning.
- Arkivläsarnas begränsningsstöd och alla tre obegränsade anrop kontrollerade mot källkod.
- H-0013-källfiler sökta i granskad main och den kopplade arbetskopian; där återfanns bara det committade protokollet.

H-0013 kan inte godkännas utan motorkoden. H-0014/H-0015 förblir REJECT, och deras siffror bör behandlas som preliminära tills datagränser, funding och portföljrisk har verifierats. Nästa steg är Claudes exakta commit och avgränsade regressionstester, utan nya hypoteskörningar eller omoptimering.

## Claudes besked via Edwin

Claude bekräftar att H-0013 endast omfattar protokollet/registreringen i d88eaac och arbetsstatus i 22b8392. Ingen Fas 2-motor, migration, könintegration, datakörning eller driftsättning finns. Det gamla utkastet är kasserat och ska inte återanvändas som verifierad kod. Detta stämmer med källkodsgranskningen ovan. Testuppgifterna i beskedet gäller register/export, inte en adaptiv motor. H-0014/H-0015 är separat arbete och fynden i tvärsnittsmotorn tillskrivs inte H-0013.

Granskningsbeslut: H-0013 är **förregistrerad, ej implementerad**. Nästa implementationssteg är regimmodul och adaptivt strategikontrakt med syntetiska tester för tidsgränser, fönsterbyte och platt läge; därefter ett separat versionshanterat kökontrakt. Inga nya verkliga körningar eller paper-godkännanden ingår i denna granskning. Tidigare REJECT gäller fortsatt.
