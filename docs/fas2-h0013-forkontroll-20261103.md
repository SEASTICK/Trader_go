# H-0013 – läsande förkontroll inför separat körbeslut, 2026-11-03

**Ingen H-0013-körning har startats.** Förkontrollen är ingen träning eller utvärdering och ger inget strategiresultat. A3 är klar enligt docs/fas2-a3-utfall-20261103.md; F2-802 är fortsatt öppen.

## Förutsättningar

- Installerad Mac-granskningsapp 9471e51, medlemssession verifierad. H-0013-vyn visar inget resultat och inga körningar.
- Förberedelsekortet är öppnat, men bekräftelserutan är **inte markerad** och Köa H-0013 är inaktiverad. Ingen köning utförd.
- Efter A3: en worker b44d3ce, PID 30868, noll omstarter, ledig slot, ingen queued/running och noll H-0013.
- Inga migrationer eller releaseändringar behövs för denna körning.

## Arkivkontroll 14:24:05 UTC

Som tjänstekontot tradergo kördes endast `verify_frozen_archives`, med paketets befintliga manifest. Alla **120** frysta utvecklingsarkiv verifierade mot filnamn, SHA-256 och Binance CHECKSUM. Endast arkiv 2020–2024 valdes och öppnades; inget slutprov lästes. Ingen OHLCV-serie laddades för utvärdering och `fas2_eval.evaluate` anropades inte.

- dataset: `6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c`;
- manifest SHA-256: `9401fa4210b8859f17476eaee5211d66814ef74fc508ea51f63f75387e14675f`.

Detta verifierar tillgängliga arkiv; den faktiska körningen måste fortfarande verifiera de inlästa staplarnas och fundingseriens hash enligt workerkontraktet.

## Det beslut som återstår

En registrerad körning från appen med fasta inställningar: BTCUSDT UM 4H, utvecklingsperiod 2020-01-01 till 2025-01-01 exklusivt, sex walk-forward-fönster 2022–2024, 200 permutationer och 81 spelböcker, oförändrade kandidater och kostnader. Workerns tidsgräns är två timmar. Misslyckade eller avbrutna försök sparas och ingen ny manuell köning görs utan nytt beslut; köns förregistrerade återförsök/lease gäller som vanligt.

Beslutet efter körningen kan bara vara REJECT eller MORE_RESEARCH. Resultatet granskas innan något förs in i registret. Detta godkänner ingen strategi för papper eller live. Slutprov och Stable-/testpublicering är separata beslut och ingår inte.

Sluttestplanens avsnitt B säger: **"Startas bara efter Edwins uttryckliga ja, från appen, med tvåstegsförberedelsen."** Förkontrollen slutar därför före bekräftelserutan och köknappen.


## Körbeslut och start

Efter förkontrollen gav Edwin uttryckligt ja till den registrerade H-0013-körningen enligt ovan, med slutprov och publicering fortsatt undantagna. Bekräftelserutan markerades i installerad app 9471e51 och Köa H-0013 trycktes **en gång**.

- Körnings-id: **ca59d441-3ab3-489b-b762-c368a6220834**.
- Workerstart **2026-11-03 14:26:29,305311 UTC**, försök **1 av 3**.
- Appen visar I kö och därefter Körs, först 0 procent och senare 66 procent. Ingen avbrytåtgärd används för denna forskningskörning.
- En worker verifierad på PID 30868/b44d3ce; beräkningsprocess 35360 observerad med ungefär 91 MB RSS. Detta är enstaka stickprov, inte en uppmätt resurstopp.
- Körningen pågår. Resultat, beslut och F2-802 godkänns inte före slutförd oberoende resultatkontroll.
