# Claude: H-0017 leverans C2 – fundingbokföring och exakta event

C1 är godkänd på **6f4350569f52527d9a156333240b735530e423a6** enligt docs/momentum-C1-granskning-6f43505.md. A2 registrerades på db7f83b och B godkändes på 3294e8f. Detta är en avgränsad implementationsdel, inget tillstånd att köra forskning eller röra drift.

## Läs och bevara

Läs AGENTS.md, CLAUDE.md, research/h0017-protokoll.md (särskilt §6, §8, §12, §15 och D18/D19), docs/momentum-status.json och föregående granskningar. Protokollet styr de exakta reglerna; ingen annan funding-/riskmodell ska införas. Bevara protokoll, register, B-modul, gamla resultat och auditfiler.

Utgå från granskningskedjan som innehåller detta uppdrag, kontrollera HEAD/diffbas/dirty/fjärrstatus och använd egen gren. Börja inte från äldre main som saknar kedjan. Ingen reset/force-push eller annan sessions ändringar ska skrivas över.

## Din enda leverans nu

Bygg fundingbokföring på **redan givna konton/positioner och syntetiska event**:

1. En fundinghändelse har exakt UTC-tid med millisekundupplösning, ändlig ränta, positivt ändligt referensmarkpris och stabil händelseidentitet. Ingen 60-sekunders tolerans, avrundning till 4H-gräns eller jämn fördelning över stapeln.
2. Betalning = q×M_ref×ränta. Positivt belopp minskar C, negativt belopp ökar C. Det ska fungera för long, legacy-short och platt. Referensmodellen är mark_open för stapeln som innehåller eventtiden, aldrig framtida mark_close i huvudmodellen. Om priset ges som argument ska dess källa/tid följa med för spårbarhet; hämta ingen verklig markdata här.
3. Utöka Account med ackumulerad **netto betald funding**, med standardvärde 0 och samma finita talvalidering. Håll funding separat från handelsrealiserat och handelskostnader. Redovisningsidentiteten blir C=C0+realized−costs−funding_net−q×avg_price. Visa att C1:s tidigare identitet är oförändrad när funding_net=0 och att gamla konstruktioner/fills fortfarande fungerar. Detta är bokföringskomplettering av protokollets redan beslutade funding, ingen ny strategi-/riskregel.
4. Skapa uttryckligt tillstånd för redan behandlade fundingevent **per konto och scenario**. Ett återanrop med samma händelseidentitet får inte debitera igen; avvisa kontrollerat utan kontoändring. Samma event ska kunna bokföras i ett annat kontos/scenarios separata tillstånd. Även ett nollbelopp på platt konto räknas som behandlat och får inte debiteras på en senare ny position.
5. Returnera oföränderliga konton och spårposter med event-id, exakt tid, q vid avräkning, ränta, M_ref och källa, betalning, C/E före och efter samt fas. Varje belopp och beräknat resultat ska vara ändligt; fel får inte ändra indata eller ge en halv bokföring.
6. Fundingstress dubblar bara faktiskt betalda positiva belopp; mottagen funding lämnas oförändrad enligt §12. Håll normal och stressad bokföring skilda och märk konfigurationen. Inga nya stresstester eller trösklar hittas på.

C2 ska inte fatta handelsbeslut eller skapa en fullständig öppnings-/intrastapelloop. För tester av A/B **komponeras** fundingfunktionen och C1-fyllningarna i den låsta ordningen: A på q före affären, B på q efter affären. Kommande eventlager ansvarar för att den position som skickas faktiskt gäller vid eventtiden och för marginal-/likvidationskontroll före fyllning. Skriv inte en till synes färdig öppningsmotor som hoppar över detta steg.

## Obligatorisk syntetisk verifiering

- Avstäm O5/O5b mot separata orakelfacit: inträde/utgång med exakt samtidig funding i A och B, E_trade bevarat som affärens kapitalfas och E_post som separat kapital efter funding. Funding ska inte räknas som avgift eller realiserad handelsvinst.
- O16: exakt vid gränsen och ±30 sekunder behåller skilda tidsstämplar/ordning och rätt UTC-dag. Använd givna positions-/fyllningssekvenser i testerna; implementera inte en egen historisk körning.
- O17: när ett givet konto redan stängts vid öppningen betalar senare funding 0; ett nytt konto/inträde använder nya positionen. En ren fundingfunktion ska aldrig återuppliva en gammal position. Full L1/L2-/stop-/likvidationsorkestrering verifieras senare.
- Long och short med positiv, negativ och noll ränta; platt konto; flera event; deduplicering; två separata konton/scenarier med samma event-id; nollbelopp som inte kan debiteras senare efter ny position.
- Fundingstress: positiva betalningar ×2, krediter oförändrade för både long och short. Kontrollera tecknet på den faktiska betalningen, inte bara räntans tecken.
- Efter funding följt av partialaffär, vändning, hold och full stängning ska nettoledgern, kostnader, handelsrealiserat och avstämning fortfarande stämma. Före/efter-spår ska ge samma kapitalförändring som bokförda belopp, med oberoende handräknade eller Decimal-facit.
- Felaktiga tider, icke-ändlig ränta/pris/belopp och overflow från ändliga argument ger kontrollerade fel utan ändrat konto/tillstånd. Numpy- och Python-tal ska bete sig lika. Lägg till riktade felprov för tecken, dubbelbokning, fel position/fas och dubblerade krediter, och återställ före commit.

## Ingår inte

Ingen marginal/likvidation, dagsreset, band-/signalbeslut, dag-/permanent-stopp, intrastapel-bound, full event-/riskloop, jämförelseutvärderare, ekonomiskt beslut, historikläsning, dataaudit/nedladdning, H-0017-jobb, kö/worker, app, SQL/server, release eller paper/live. De tillkommer först efter nästa granskning. Ingen ny marginalregel ska döljas i fundingfunktionen om kapital blir lågt; rapportera bokförd ändring till kommande risklager och följ protokollet där.

Om en materiell lucka i det frysta kontraktet upptäcks ska den redovisas till Codex innan en annan regel kodas. Ändra inte protokollet för att passa implementationen.

## Status och återrapportering

C2 ger främst delunderlag för MOM-C03. Hela C03 är inte klar förrän även dagsreset och första/sista event är integrerade och granskade. C05 är fortsatt öppen. Eftersom Account och avstämningsidentiteten kompletteras ska MOM-C01 återöppnas till in_progress tills Codex omgranskat den nya ledgerrevisionen, trots att gamla tester passerar. Bevara A/B om de är orörda.

Kör relevanta ledger-/funding-/signal-/registertester, tidigare orakel/audits i projektets venv och checklistgeneratorn med --check. Markera nya C-punkter in_progress med exakt underlag. Lämna gren, HEAD, diffbas, ändrade filer, API/versionskontrakt, identiteter, orakelavstämning, faktiskt testutfall, felprov, påverkan på C1-verifiering och kvarstående begränsningar. Nästa C-del väntar på Codex godkännande.
