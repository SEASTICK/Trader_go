# H-0017 C6-01 – Codex granskning av dokumenterat beslut

Datum: 2026-11-04. **Bedömning: BEHÖVER RÄTTAS i beslutsunderlaget. Edwins val är korrekt återgivna och omprövas inte.**

Granskad revision: `e46624820920909cddd1ad29f7122da3d5f8ebdc`, gren `codex/momentum-c6-review`. Full HEAD och gren kontrollerades; arbetskopian var ren före granskningen (`git status --short` och `git status --porcelain=v1` tomma).

Granskningen avser [Edwins dokumenterade beslut](momentum-C6-01-edwins-beslut.md) och [det rättade underlaget](momentum-C6-01-beslutsunderlag.md), mot [Codex valfrågor och tidigare fynd](momentum-C6-01-granskning-underlag.md), [C6-uppdraget](claude-uppdrag-momentum-C6.md), [C5-01](momentum-C5-01-edwins-beslut.md), [ordningsbeslutet](momentum-C5-01-ordningsbeslut.md) och [frysta protokollet](../research/h0017-protokoll.md), särskilt §8.3, §9, §10 och §13. Edwins svar `1=H1, 2=I1, 3=G1, 4=P1` är även uttryckligen bekräftat i granskningsuppdraget. Claude-chatten har inte inspekterats separat; uppgiften om hur frågorna presenterades är dokumenterad proveniens, inte en oberoende verifierad chattgranskning.

## Bekräftat kontrakt

Beslutsdokumentets fyra punkter motsvarar de valda alternativen utan nytt materiellt val. P1 har korrekt specialiserats till H1: nollan följer low, och H3-grenen är därför borttagen. Att olösta mellanevent aldrig bokförs är C5-01, inte ett tillagt Edwinval.

1. **Intrastapelträff:** bevara C5:s faktiska öppningsordning och C6-uppdragets kapitalfaser: gap/open på ingående C/q före A-funding och fill, därefter tillåtna öppningssteg, E_trade efter affär före B-funding och E_post efter öppningens funding. Sedan hypotetisk high, hypotetisk low, likvidationsnolla och faktisk close 0. Open ska inte räknas på q_open om öppningen ändrat positionen. High/low använder q_open före nollställningen. Punktordningen är ingen observerad tidsordning mellan extremer, träff och funding.
2. **Fundingbas:** C_post är kapitalbasen efter öppningens fullständiga steg. För alla olösta mellanevent används signerad betalning p_i (positiv betalas), med q_open och M_ref=mark_open: C_high=C_post−Σmin(p_i,0), C_low=C_post−Σmax(p_i,0). E_high=C_high+q_open×mark_high och E_low=C_low+q_open×mark_low. Beloppen används endast hypotetiskt; öppningens A/B-funding står kvar och mellaneventen förblir olösta i ledgern. Marginalunderlag och träffflagga ändras inte.
3. **Negativa värden:** I1 behåller alla valda negativa kapitalpunkter före reset oklippta, inte bara low. G1 behåller rått negativt gap-/öppningsprövningskapital före nollan. Drawdown får understiga −100 %. Detta legitimerar inget oförklarat negativt levande konto utanför dokumenterad träff.
4. **Gap/öppningsträff:** bevara endast C5:s gap-, A- och prövningssteg som faktiskt hunnit ske, i deras verkliga ordning och med deras proveniens, därefter likvidationsnollan. Vid träff redan i gapet är sekvensen gapvärde, nolla; ingen räddande fill, B-funding eller trade/post/high/low med gammal position skapas efter känd öppningslikvidation.
5. **Nollpunkt, peak och minimum:** faktisk close och terminal är 0. Därefter endast absorberande noll utan affär, funding eller återupplivad exponering. Boundens egen peak börjar vid 100 000 och uppdateras i punktordning, inklusive high före low. Tidigare peak och tidigare drawdownminimum bevaras vid likvidation och senare staplar. För varje punkt gäller peak=max(tidigare peak,E) och minimum=min(tidigare minimum,E/peak−1). Ingen peakreset eller 0/0. Hela förloppets minimum är min(tidigare minimum, lokalt minimum).

Reservationen om konservativitet är korrekt: vid negativ trough gör högre positiv peak kvoten mindre negativ. Båda angivna exakta kvoterna stämmer. Valet får därför inte beskrivas som bevisat strängast under −100 %. För en giltig main-körning med likvidation är protokollets C6 redan falskt; detta ändrar redovisningen, inte den ekonomiska klassificeringen. OGILTIG/OGILTIG_DATA är separata frågor.

Avgränsningarna är korrekta: huvudmodell long/platt, inget legacybeslut, ingen återkoppling till handel, ingen ändring av close-serie, marginal eller ledger. Tillägget skriver inte om protokollet eller C5-01. Revisionsdiffen från den tidigare granskade basen visar endast de två C6-01-dokumenten samt den tidigare granskningsfilen; inga ändringar i protokoll eller C5-01.

## Fel som måste rättas

**1. Den tidigare granskningens kompletterande konsekvensexempel saknas.** Rättningsavsnittet tar upp alternativens oberoende, fundingalternativet, gapets M_ref, historikförbehållet, konservativitetsreservationen och beslutsnamnet. Men tidigare granskning krävde uttryckligen även en high som höjer peak och ett tidigare negativt boundminimum. Underlaget innehåller fortfarande bara fall där high inte höjer peak. Lägg till syntetiska ordnade punkter med oberoende facit för dessa två förhållanden, med lokal respektive ackumulerad drawdown tydligt skilda. Inga marknadsdata eller nya val krävs. Reservationens jämförelse med peak 120 000 ersätter inte en visad punktsekvens som uppdaterar peak.

**2. Underlagets kvarvarande huvudtext måste avgränsas eller rättas där den motsäger rättningsavsnittet och kontraktet.** Avsnittet ”Konsekvens” säger fortfarande ”REJECT/PASS eller något beslut” och att B/C ger exakt magnitud 1 utan historikförbehåll. Begränsa slutsatsen till ekonomisk klassificering av giltig main-körning med oförändrade övriga serier; använd REJECT/MORE_RESEARCH och skilj lokalt bidrag från ackumulerat minimum. I alternativ A står dessutom att open, trade, post, high och low räknas med q_open: korrigera detta så att open använder ingående C/q, medan high/low använder q_open. Att det syntetiska exemplet saknar affär gör formuleringen numeriskt osynlig där, men den är inget korrekt generellt implementationskontrakt. De äldre A/B/C-frågorna är uttryckligen ersatta av H/I/G/P och ska inte användas som styrande val.

Det krävs inget nytt beslut från Edwin och ingen omprövning av H1/I1/G1/P1. Rätta underlaget enligt ovan och låt Codex kontrollera rättningen innan C6-01 lämnas som komplett klartecken för berörd implementation.

## Verifiering och leveransgräns

Dokumentjämförelse och revisionsdiff har granskats. Ingen produktionskod, syntetisk motorsvit, historikkörning eller audit har körts; detta godkänner ingen implementation eller full C6/MOM-C04-leverans. Endast denna granskningsfil skapas enligt det uttryckliga uppdraget; status och checklistor lämnas orörda. Ingen commit. H-0013 förblir REJECT och H-0016 berörs inte.
