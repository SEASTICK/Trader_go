# Claude: H-0017 leverans C1 – ledger, storlek och kostnad

B är godkänd på **3294e8f992818e9f988077eafb2e6ef110be86f0** enligt docs/momentum-B-granskning-3294e8f.md. A2 registrerades i db7f83b. Detta är första avgränsade delen av C, ingen ändring av fryst metod och inget godkännande av forskningskörning.

## Läs och bevara

Läs AGENTS.md, CLAUDE.md, research/h0017-protokoll.md (särskilt §6, D17/D19 och orakel), docs/momentum-status.json och B-godkännandet. Projektets skill .claude/skills/riskgranser/SKILL.md är riskbakgrund; det godkända H-0017-protokollet styr konkreta parametrar och storleksmodell. Lägg inte till en annan ATR-/stopbudget eller nya strategi-/riskregler.

Utgå från granskningskedjan som innehåller detta uppdrag; börja inte från äldre main. Kontrollera HEAD, diffbas, fjärrstatus och ocommittade ändringar. Använd egen gren. Bevara B-modulen, fryst protokoll, register, gamla resultat och andra sessioners arbete; ingen reset/force-push. Skapa ingen parallell backtestmotor i Rust/frontend.

## Din enda implementation nu

Bygg den rena konto-/utförandegrunden för mom-ledger/1.0.0 enligt protokollets §6:

1. Ett konto med kontantekvivalent C och signerade enheter q; E=C+q×M. Markpris värderar kapital, kontraktspris används för fyllning. C är inte bokstavlig spotkassa. Kortpositioner behövs endast för de frysta legacy-kontrollerna, aldrig för H-0017 main.
2. Enhetsändringen Δq handlas en gång. C minskas med Δq×P+c×P×abs(Δq). Normalkostnad c=0,0016, kostnadsstress c=0,0040. Inga dubbla spread-/slippagepåslag, inga syntetiska fulla stängningar/återöppningar vid partialjustering.
3. Implementera den frysta kostnads-/basisjusterade storlekslösaren och dess grenval exakt enligt §6. Testa köp, sälj, oförändrade enheter, full stängning och vändning. Validera felaktiga/icke-ändliga värden och ogiltiga lösningar uttryckligt. Ingen dold klippning, lotavrundning eller epsilonkapital.
4. Separera normal fyllning från mekanisk reduce-only-fyllning av en redan given riskavsikt. Reduce-only kan ge loggad risk_reduce_only_hold efter gap och går då före exakt målvikt. Skapa inga dags-/riskavsikter här; deras beslut och prioritet kommer i nästa del av C. w=0 ska ge full stängning enligt kontraktet.
5. Spara E_trade som kapital efter affär. Målidentitet/cap ska inte testas mot ett framtida E_post efter funding. C1 implementerar inte funding, men API:t ska kunna lämna spårbar information till dess senare eventsteg.
6. Genomsnittligt inträdespris och realiserat resultat ska hantera partialminskning och vändning utan fiktiva avslut. Kostnad bokförs bara en gång i kontot; håll kapitalledgern som källa för avstämning.

Välj avgränsad modulstruktur inom engine/traderlab och dokumentera API/typer, rena in-/utdata, feltyper och bokföringsidentiteter. Befintliga rena statistik-/signalmoduler återanvänds utan förändring. Syntetiska testkonton får ha mindre kapital för handräkning; verklig körningskonfiguration är fortsatt låst till protokollet.

## Obligatorisk syntetisk verifiering

- Stäm av O1–O4 i docs/momentum-a1-orakel.json med oberoende förväntningar. Återanvänd inte produktionslösaren för att skapa testets facit. Kontrollera C, q, Δq, markvärde, kostnad och vikt med protokollets toleranser.
- Normal w=1 efter kostnad ska uppfylla identiteten utan kostnadsdriven överexponering. Basis där P≠M ska räknas exakt en gång.
- Partialköp, partialsälj, oförändrat innehav, full stängning, long→short och short→long för legacy-grunden. Vändning är en sammanlagd Δq, inte två kostnadsbokföringar på samma belopp.
- O14: C=800, q=2, riskmålvikt 0,195. Gap till 90 ska behålla q=2 utan kostnad och logga hold; gap till 110 ska minska exakt. Normalavsikt enligt O15 får byta handelsriktning när fryst målvikt fylls efter gap.
- No-trade får inte ombalansera eller ta avgift. Att multiplicera startkapital och innehav med en konstant ska skala beloppen men bevara relativa mått.
- Felaktig/icke-ändlig indata, icke-positivt kapital/pris och inkonsekventa lösargrenar får inte läcka NaN eller tyst ändra reglerna.
- Lägg till riktade avsiktliga fel som testerna faktiskt fångar, exempelvis kostnad två gånger, storlek före i stället för efter kostnad, ignorerad basis, riskavsikt som ökar q eller partialsälj som realiserar hela positionen. Återställ varje fel före commit.

## Gränser för kommande lager – ändra dem inte

| Gräns | Låst värde | Var den ska kontrolleras | Vem får ändra |
|---|---|---|---|
| Målvikt/cap efter affär | main högst 1× och dagens cap, enligt E_trade; fundingdrift hanteras separat | mekanisk storlek nu, avsiktslager senare | nytt hypotes-id och granskat protokoll, ingen körtidsknapp |
| Normalt handelsband | 2 procentenheter, högst ett normalt dagsbeslut | senare del av C | som ovan |
| Dagsstopp | 2 % nettokapital | senare del av C, closebeslut/nästa öppning | som ovan |
| Permanent stopp | 15 % från nettokapitalets stängningspeak | senare del av C | som ovan |
| Godkännandegräns drawdown | 20 % close och konservativ bound | senare risk-/utvärderingslager | som ovan |

Gap kan överskrida stoppnivåer. Ingen garanti om maximal förlust ska beskrivas. Detta är historisk forskningskod, inte live- eller paperdrift.

## Ingår inte i C1

Ingen schemalagd eventloop, funding, marginal/likvidation, UTC-dagsreset, handelsband-/signalbeslut, dag-/permanent-stopp eller intrastapel-bound implementeras ännu. De kommer efter Codex granskning av ledgergrunden. Ingen jämförelseutvärderare, statistikbeslut, huvudstrategiurval, faktisk dataaudit/historikläsning/nedladdning, 2025-åtkomst, H-0017-jobb, kö/worker, app, SQL, server, release eller paper/live.

Om ett materiellt tolkningsproblem upptäcks i fryst §6: redovisa det innan en annan regel implementeras. Ändra inte protokollet i denna leverans.

## Status och återrapportering

C1 ger främst underlag för MOM-C01 och delar av C05. Markera inte hela C02–C05 klara när deras senare event-/risklager saknas. Nya relevanta C-punkter står in_progress tills Codex granskat exakt revision. Bevara A/B som klara om deras underlag är orört. Regenerera momentumchecklistan och kör --check samt relevanta ledger-/signal-/registertester och tidigare audits med projektets venv.

Lämna gren, HEAD, diffbas, ändrade filer, API/versionskontrakt, orakelavstämningar, tester med verkligt antal/utfall, avsiktliga felprov och kvarstående begränsningar. Nästa del av C börjar först efter Codex godkännande av exakt C1-revision.
