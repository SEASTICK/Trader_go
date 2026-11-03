# Claude: H-0017 leverans B – ren signalmodul och tidskontrakt

A2 är godkänd av Codex på exakt registreringscommit `db7f83b56e79f8a76b5e0d297be4503170070c0f`. Läs docs/momentum-a2-granskning-db7f83b.md, research/h0017-protokoll.md, AGENTS.md, CLAUDE.md och docs/momentum-status.json före arbete.

## Utgångsläge och omfattning

Utgå från den granskningsgren/commit som innehåller detta uppdrag och hela A2-kedjan; börja inte från äldre main som saknar den. Kontrollera Git-status, HEAD, diffbas och andra sessioners ändringar. Använd en egen implementationsgren och bevara allt tidigare arbete utan force-push/reset. H-0017 är nu registrerad; skapa inget nytt id och ändra inte fryst protokoll, registerrad, gamla hypoteser eller resultat.

Implementera endast **mom-signal/1.0.0** och dess syntetiska tester. Leverans B motsvarar MOM-B01–B05. Inget konto, ledger, handelsband, order-/fill-, avgifts-, funding-, marginal- eller riskstoppslager implementeras här; det är senare leveranser. Bandet är kvar i protokollet men signalmodulen avgör inte om en affär ska ske.

## Låsta beräkningar

- Använd endast stängda 4H-staplar och kompletta UTC-dygn enligt protokollets §3–§5. Dagsclose är kontraktets close på dagens 20-stapel och är tillgänglig först vid nästa 00:00.
- s_h(D)=1 om C_D/C_(D−h)−1>0, annars 0, för h=7,14,28 kalenderdagar. Lika pris ger 0. s är medelvärdet; inga vikter tränas.
- Beräkna de senaste **60 enkla dagsavkastningarna**, vilket kräver 61 dagsstängningar, med ddof=1 och annualisering sqrt(365).
- cap=min(1,0,10/vol), w_target=s×cap. Long/platt; ingen short, ATR, regimstyrning eller optimering.
- Saknad uppvärmning eller icke-ändlig/icke-positiv volatilitet ger uttrycklig otillgänglig signal, ingen division med noll och ingen tyst ersättning med platt/full vikt. Under en bedömningsperiod är sådan otillgänglighet OGILTIG_DATA enligt protokollet; det framtida körlagret får inte tyst handla vidare.
- Saknade kalenderdagar/staplar får inte ersättas med ett annat antal observationer, interpoleras eller framåtfyllas. Avvisa felaktiga tidsindex/priser enligt kontraktet i stället för att sortera/rensa dem i smyg.

Ge modulen ett tydligt versionsmärkt gränssnitt och dokumentera fält, tillgänglighet samt beslutets tidsstämpel. Tidsinformationen ska räcka för att nästa lager kan fylla tidigast vid nästa öppning utan att signalmodulen tittar på det öppningspriset. Välj fil/API inom befintlig struktur; återanvänd rena hjälpfunktioner där de följer kontraktet och skapa ingen konkurrerande forskningsmotor.

## Meningsfulla syntetiska tester

- Oberoende handräknade förväntningar för horisonterna, deras medel och målvikten; stigande/fallande/lika priser och s=0,1/3,2/3,1.
- Rätt 60 avkastningar/61 stängningar, ddof=1 och sqrt(365), inklusive första tillgängliga dag. Skilj avkastningsserien från prisernas standardavvikelse och från logavkastning.
- UTC-dagsgräns och komplett/saknad/pågående sista dag. Visa exakt när dagens sista close får påverka signalen och att dagens signal inte används på tidigare staplar samma dag.
- Prefixprov och ändrade framtida priser: framtida data får inte ändra tidigare tillgängliga signaler. En framtida stapels öppningspris får inte påverka ett redan fattat beslut.
- Saknad mellandag/stapel, feljusterade tidsstämplar, dubbletter, osorterat index, fel tidszon samt icke-ändliga/ogiltiga priser hanteras uttryckligt enligt kontraktet. Noll eller ogiltig volatilitet är otillgänglig signal, inte köp.
- Riktade felprov ska visa att testerna fångar relevanta fel, exempelvis egen dags framtida close, observationsantal i stället för kalenderdagar, 60 i stället för 61 stängningar, ddof=0, fel annualisering eller ändrade signalvikter. Återställ de avsiktliga felen innan commit.

Använd endast syntetiska indata. Ingen läsning, audit, nedladdning eller körning mot riktig marknadshistorik i B. Starta ingen H-0017-körning eller kötest. Om en materiell oklarhet i fryst kontrakt upptäcks: rapportera den till Codex innan en annan regel kodas.

## Tillåtna ändringar och återrapportering

Avgränsad signalmodul, nödvändiga rena hjälpfunktioner, syntetiska tester, kort API-dokumentation och berörda status/checklistor. Undvik ändringar i redan verifierade moduler om återanvändning räcker; redovisa varje sådan påverkan. Ingen app, SQL, worker, server, release, marknadshistorik eller paper/live ingår.

Kör relevanta signal-/register-/statistiktester och befintliga kontroller som berörs. Använd projektets venv för tidigare audit-script och orakel. Uppdatera MOM-B01–B05 med underlag; nya implementerade punkter ska stå in_progress tills Codex granskat exakt revision. Regenerera momentumchecklistan och kör --check. Bevara godkänd A-status om dess underlag inte ändrats.

Lämna gren, HEAD, diffbas, ändrade filer, API/versionskontrakt, tidsregler, tester med faktiskt antal/utfall, felprov, vad som bara är syntetiskt prövat och kvarstående begränsningar. Leverans C börjar först efter Codex godkännande av B.
