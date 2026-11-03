# Codex slutgodkännande av H-0017 leverans B

Datum: 2026-11-03. Godkänd revision: **`3294e8f992818e9f988077eafb2e6ef110be86f0`**, diffbas `b0f0cfe`.

**Leverans B godkänns. P2-fyndet om signals(empty) är stängt. Inga nya blockerande fynd.** Godkännandet avser mom-signal/1.0.0 och dess syntetiskt verifierade tids-/beräkningskontrakt. Konto, utförande, verklig data och ekonomiska resultat ingår inte. Leverans C får börja med den avgränsade C1-instruktionen.

## Oberoende kontroll av rättningen

- signals bygger nu alla signalkolumner med uttryckliga typer även för noll rader. Tom UTC-ram och tomt prefix ger exakt COLUMNS, UTC-index och UTC-tidskolumner, numeriska signalfält, boolesk available samt object för reason/version.
- latest_decision på båda tomfallen ger det dokumenterade KeyError-meddelandet om inget känt beslut. Ingen dagsrad eller nollvikt uppfinns.
- En icke-tom ofullständig dag ger fortsatt incomplete_day, available=false och otillgänglig målvikt.
- AST-jämförelse visar att validate_bars, daily_closes och latest_decision är oförändrade samt att signals beräkningsdel före utmatningsbygget är oförändrad. Rättningen ändrar hur resultatet byggs, inte formlerna eller tidpunkterna.
- För **17 icke-tomma syntetiska fall** ger gamla bfdb33b och nya 3294e8f identiska DataFrames inklusive typer, index och värden: kort uppvärmning, kompletta/ofullständiga sista dagar, längre serier, saknad stapel/dag och konstant pris.
- Den gamla revisionens KeyError reproduceras fortfarande för de två tomfallen; den nya ger stabilt schema. Detta verifierar skillnaden, utan att skriva om Claudes fil.

Reproduktion: `engine/.venv/bin/python research/audits/momentum-b-3294e8f/review.py --check`. Skriptet läser de två låsta Git-versionerna och använder enbart syntetiska staplar. verification.json sparar källhashar och utfall. Äldre B-audit kör fortfarande den historiska bfdb33b och är bevarad som underlag, inte som ett misslyckat prov av den rättade revisionen.

## Tester och integritet

- **36 signaltester godkända**, inklusive de fyra nya tomdata-/uppslagsregressionerna.
- **589 tester godkända i hela motorsviten**, exit 0. Testantalet verifierades genom insamling. Samma befintliga joblib-varning om fysiska CPU-kärnor förekom; den gav inget testfel.
- A1-orakel, de fem tidigare Codex-audits och samtliga fyra checklistgeneratorer passerar i projektets venv. Ny audit passerar också.
- Fryst H-0017-protokoll och register är oförändrade mot e66d730. Inga befintliga beräkningar eller modellparametrar har ändrats. Arbetskopian var ren före granskningen, och lokal/fjärr claude/momentum-b verifierades på samma fullständiga hash.
- git diff --check för b0f0cfe..3294e8f är rent. Claudes rapporterade 14 mutationsprov är hans underlag; Codex oberoende felprov på bfdb33b och den nya före/efter-kontrollen anges separat.

MOM-B03 och MOM-B05 markeras klara. B01/B02/B04 bevaras som klara och får kompletterande underlag för den oförändrade beräkningsdelen på 3294e8f. A+B är därmed **10/40**. Inga C-punkter markeras påbörjade eller klara genom enbart denna handoff.

## Nästa leverans och kvarstående begränsningar

Följ [Claude-uppdraget för C1](claude-uppdrag-momentum-C1.md). Det delar implementationsarbetet i granskningsbara steg, utan att ändra protokollet: först ledger/storlek/kostnad, därefter event-/funding-/risklagret efter nästa granskning. Ingen utvärderare, dataaudit, historisk körning, kö, server, migration eller release ingår.

B är en ren signalmodul för stängda staplar. Att bara stängda/stödda data når modulen samt historikskydd och OGILTIG_DATA i det verkliga körflödet ska verifieras senare. Markprisapproximation, fasta marginalsatser, kontinuerliga enheter och redan sedd utvecklingsperiod är oförändrade forskningsbegränsningar. Ingen strategi är godkänd för paper/live; H-0013 REJECT och H-0016 är orörda. Tidigare Windows-/Gatekeeper-/larm-/temabegränsningar är inte omprövade här.
