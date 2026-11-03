# Codex granskning av H-0017 leverans C2

Datum: 2026-11-03. Granskad revision `1d9359fe71259a9099ac7443993a48dfa8c1423f`, diffbas `96f4520`.

**Fundingbeloppen och ledgerkompletteringen stämmer, men C2 behöver två API-rättningar före godkännande.** Det gäller implementationsvalidering, inte nya ekonomiska regler eller ändring av protokollet. C01 kan återmarkeras klar för den utökade ledgern på denna revision; C03 och C05 är fortsatt öppna.

## C2-01 [P2] Kontrollera att fundingfasen passar eventets exakta tid

Plats: `engine/traderlab/momentum_funding.py:149–150`.

apply_funding kontrollerar bara att phase är ett av tre tillåtna namn. Funktionen accepterar därför ett event vid 00:00:30 som funding_A eller funding_B, och ett event exakt 00:00 som funding_interior. Kontot debiteras och spårposten får den oförenliga fasen utan fel.

Med C=50 000, q=500, M_ref=100 och ränta 0,0001 returnerar samtliga dessa fall en betalning på 5. Det är beloppsmässigt samma sak för det givna kontot, men fasen är inte fri metadata: enligt §8.3 gäller A/B endast vid exakt 4H-gräns, medan mellanhändelser ska förbli mellan öppning och close. En felmärkt rad kan senare behandlas med fel positionsfas eller ge missvisande spårbarhet.

**Krävd rättning:** före bokföring, kräv event.time=bar_open(event.time) för funding_A/funding_B och strikt mellanliggande tid för funding_interior. Detta väljer inte position och kräver ingen eventloop; det kontrollerar bara två redan tillgängliga uppgifter. Fel ska ge FundingError och lämna konto/state oförändrade. Behåll full millisekundprecision utan tolerans eller avrundning.

**Regressioner:** gräns, ±30 sekunder och ±1 millisekund över alla tre faser. Rätta också befintliga tester som idag matar en icke-samtidig händelse i funding_A eller gränshändelser i funding_interior, exempelvis millisekundtestet och sekvenstestet. Behåll deras ekonomiska facit; korrigera tid/fas så fallen faktiskt följer protokollet.

## C2-02 [P2] Validera behandlade event-id innan FundingState normaliseras

Plats: `engine/traderlab/momentum_funding.py:109–114`.

FundingState omvandlar varje argument med frozenset utan att kontrollera samlingens typ eller innehåll. `FundingState('main', 'A', processed='f1')` blir därför frozenset({'f', '1'}) i stället för ett kontrollerat fel. Om ett redan behandlat id råkar återställas som sträng missar dubbelbokningskontrollen hela id:t och samma event kan debiteras igen.

Reproduktion på ett korrekt konto: boka event f1 en gång (C 50 000→49 995, funding_net 5). Konstruera ovanstående felaktiga state och boka samma event igen på det resulterande kontot. Funktionen accepterar det och ger C=49 990, funding_net=10. En korrekt frozenset({'f1'}) avvisar däremot återanropet. Felet ligger i tyst omtolkning av felaktigt state, inte i den normala set-kontrollen.

**Krävd rättning:** processed ska vara en uttryckligt stödd samling av hela, icke-tomma sträng-id. Avvisa ensam str/bytes, None och ogiltiga element med FundingError innan normalisering. Valid samling får inte byta betydelse. Samma validering ska gälla dataclasses.replace och eventuell återställningsväg. Ingen global cache införs; state för separata konton/scenarier ska fortsatt vara separata.

**Regressioner:** felaktig sträng, bytes, None, tal/bool/None/tom sträng som element, korrekt tom samling och giltiga samlingar som bevarar hela id. Visa att korrekt återställt behandlat f1 avvisar en andra bokning utan kontoändring och att separata konton/scenarier fungerar som tidigare.

I samma avgränsade API-rättning bör M_ref_source valideras som sträng innan dictionary-uppslaget på rad 94. En lista som källa ger idag TypeError för en ohashbar nyckel i stället för det dokumenterade FundingError. Det är en relaterad feltypslucka, inte en ny ekonomisk metodfråga.

## Verifierade delar och C01

- **47 fundingtester och 82 ledgertester godkända**, 129 tillsammans.
- **718 godkända i hela motorsviten**, exit 0, antal kontrollerat med insamling. Den befintliga joblib-varningen om fysiska CPU-kärnor förekom i ML-testet utan testfel.
- Egen 50-siffrig Decimal-kontroll: **400 funding-/stressfall**, med long/short/platt, båda räntetecken och noll, stress enligt betalningens tecken, kontoavstämning och deduplicering med giltigt state. Alla stämmer.
- Den oberoende C1-referensens **250 storleks-/reduce-only-fall** passerar på den utökade ledgern. funding_net har default 0, egen numerisk validering och korrekt tecken i avstämningen. Funding ändrar inte q, handelsrealiserat eller handelskostnader. Gamla 82 C1-tester är oförändrade och passerar.
- **MOM-C01 godkänns åter på exakt 1d9359f.** C2:s två API-fynd ligger i fundingmodulen och blockerar C2:s slutgodkännande, men ogiltigförklarar inte den verifierade kontoklassens ändring. Ändras ledgern på nytt behöver berörd verifiering omprövas.
- A1-orakel, åtta tidigare audits och fyra checklistgeneratorer: PASS med projektets venv. git diff --check är rent. Claudes 15 mutationsprov är hans underlag; Codex påstår inte att hela hans mutationsserie körts om.
- Lokal/fjärr claude/momentum-c2 verifierades på samma fullständiga hash med ren arbetskopia före granskning. H-0017-protokoll, register och B-modul är orörda. Ingen app, migration eller driftkod ändrad.

Reproduktion: `engine/.venv/bin/python research/audits/momentum-c2-1d9359f/review.py --check`. Skriptet läser de matchande, låsta ledger-/fundingkällorna från Git på 1d9359f, kör syntetiska fall och sparar källhashar/resultat i verification.json. Ingen marknadshistorik eller extern tjänst används. Skriptet reproducerar den historiska granskade revisionen även efter senare rättning.

## Status och nästa leverans

C01 återmarkeras done med ny evidens. C03 förblir in_progress: fundingdelen behöver ovanstående rättningar och dagsreset/första/sista event återstår. C05 är fortsatt in_progress för kommande marginal-/likvidations-/riskordning. Checklistan blir **11/40**. A/B-godkännandet bevaras.

Claude rättar C2-01/C2-02 och den relaterade feltypsluckan, kompletterar regressioner och API-dokumentation samt lämnar exakt ny revision/diffbas för omgranskning. Protokoll, register och B ska vara orörda. Ändras inte ledgern kan C01 behålla godkännandet på 1d9359f. Ingen nästa C-del, verklig historik, H-0017-jobb, server, migration, driftsättning eller publicering ingår. C2 är ännu inte slutgodkänd.
