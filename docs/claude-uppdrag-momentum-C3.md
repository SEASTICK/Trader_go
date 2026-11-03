# Claude: H-0017 C3 – avsikter, band och riskstatus

C2 godkänns på **fcf5cb4a42f76b6151a8fe66f0c87f9617e95430** enligt docs/momentum-C2-granskning-fcf5cb4.md. Utgå från granskningsgrenen som innehåller detta uppdrag, inte äldre main. Kontrollera HEAD, diffbas, dirty-läge och fjärrstatus; använd egen gren utan reset, force-push eller överskrivning av annan session. Läs AGENTS.md, CLAUDE.md, research/h0017-protokoll.md och relevanta A/B/C-granskningar.

## Enda leveransen

Implementera en separat, versionsmärkt modul för **rena beslut och oföränderlig riskstatus**, med syntetiskt tillförda close-värden och signaler. Detta är inte en historisk eventmotor. Protokollets §4, §6–8, D07/D17/D19 styr; läs deras exakta ordning före kodning. Ingen 30-minutersvariant eller ny regel införs.

1. Vid varje 4H-close: beräkna/ta emot verifierbart E_close, uppdatera close-peak från initialt 100 000 och pröva permanent −15 % respektive dagsstopp −2 % på rätt kapitalbas. Spara tidsstämpel, källstapel, kapitalbas och orsak. Permanent stopp är absorberande. Alla indata och beräknade värden valideras; ofullständig/otillgänglig signal får aldrig tyst ersättas med noll/full vikt. Hantera eventuellt dokumenterat likvidationstillstånd separat från levande konto; uppfinn inte likvidationsbokföring här.
2. Bara vid dagsbeslutet efter stängningen av 20-stapeln: §7:s exakta prioriterade val – permanent spärr, platt signal med position, capbrott, absolut viktavvikelse minst 0,02, annars hold_units. Capbrott och platt signal är riskavsikter även inom bandet. Signalen/target kommer från B:s låsta kontrakt. Normalbeslut förekommer högst en gång per dygn.
3. En avsikt fryser vikt och typ, inte enheter eller köp/sälj-riktning. Håll beslutets då kända pris skilt från senare öppningspris. Fyllningarnas storlek och reduce-only ägs av C1, fundingbokföring av C2. Bevisa med kompositionstester att en normalavsikt kan byta riktning efter gap, medan en riskavsikt aldrig ökar positionen.
4. Sammanslagning för samma fyllningstid: högst en avsikt till fyllningslagret enligt terminal > permanent > dagsstopp > capbrott/platt > normal. En riskavsikt stryker normalavsikten även om dagslåset sedan upphör. Inga dolda ombalanseringar eller dubbla order.
5. Dagsreset sker efter föregående dags close-beslut: ny day_start = föregående 20-stapels E_close, före gap/funding/handel. lock_day gäller dagen för stapeln som stängde; vid ny dag upphör den gamla köpblockeringen, men redan köat riskutträde fullföljs. Permanent stopp återställs aldrig. Käll-/besluts-/tidigaste fyllningstid ska vara uttryckliga UTC-tider; avvisa ogiltig tidsordning eller dubbel behandling i samma state i stället för att tyst skapa fler beslut.
6. Beskriv API, tillståndsövergångar och gränsen till kommande eventloop. Stoptrösklar är −2 % och −15 %. 20 % är protokollets utvärderingskrav för drawdown, **inte ett nytt handelsstopp**. Terminal/första öppning är låsta enligt §4; testa avsiktsprioriteten för terminal utan att bygga en skenbart fullständig historisk körning.

## Obligatoriska prov

Använd oberoende handräkning/orakel, inte förväntade resultat hämtade från den nya produktionsfunktionen. Läs orakelfilens faktiska fall och återanvänd de som avser dagsreset/risk och gap.

- Band precis under, på och över 2 procentenheter, åt båda hållen; ingen extra epsilon. Samma sak för −2 %/−15 % på beräknade floatvärden. Använd robusta fixturer och redovisa faktiska gränsvärden.
- Capbrott trots litet bandavstånd, platt signal trots litet bandavstånd, samt båda utan position. När villkor sammanfaller ska den frysta prioriteten bestämma.
- Close-peak uppdateras rätt, funding/kostnader påverkar E_close genom kontot och bokförs inte igen av riskmodulen. Gap/funding efter midnatt får inte flytta föregående dags day_start eller peak bakåt.
- Dagsstopp inom dygnet blockerar köp i samma lock_day; stopp vid sista 20-stapelns close behåller sitt riskutträde över reset även om ny dags köpblockering upphör. Permanent stopp överlever alla reset.
- Risk och normal samtidigt ger enbart risk, med rätt fryst vikt. Komponera med C1:s gap-/reduce-only-fall. Ingen gammal normalavsikt återkommer efter riskfyllning/hold.
- Inga dagliga normalbeslut vid 04/08/12/16/20-gränser; normalbeslut bara 00. Ingen framtida information, indata oförändrade, prefix-/framtidsändring ger samma tidigare beslut.
- Felaktiga tillstånd, UTC/tider, NaN/infinity, overflow och feltyp ger kontrollerat fel utan halv uppdatering. Definiera och testa återanrop/dubbelhändelse.
- Riktade avsiktliga fel för bandets gräns, prioritet, resetens kapitalbas, borttappat riskutträde vid midnatt, permanent stopp som återställs och avsikt som fryser q i stället för vikt. Återställ före commit.

## Gränser och rapport

Ingen marknadshistorik, dataaudit/nedladdning, H-0017-körning, marginal-/likvidationsmotor, intrastapel-bound, full eventloop, jämförelseutvärderare, kö/worker, app, SQL/server, release eller paper/live. Bevara protokoll/register, gamla resultat, godkända B/C1/C2 och historiska audits. Om ett materiellt kontraktsval saknas, redovisa till Codex före ny regel; ändra inte det frysta kontraktet.

Uppdatera MOM-C02 och berörda delar av C03/C04/C05 som in_progress med exakt scope och underlag. Ingen hel punkt bockas av av Claude. C03 och C04 blir inte kompletta genom enbart rena tillståndsfunktioner; första/sista event, marginal och intrastapelrisk integreras/granskas senare. Ändras godkänd kod, återöppna berörd verifiering enligt AGENTS.md.

Kör relevanta tester, hela motorsviten, A1-orakel, tidigare revisionslåsta audits och alla fyra checklistgeneratorer med --check i projektets venv. Återrapportera gren, full HEAD, diffbas, ändrade filer, API/version, oberoende facit, testutfall, mutationsprov, statuspåverkan och kvarvarande gränser. Nästa C-del väntar på Codex granskning av exakt revision.
