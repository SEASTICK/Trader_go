# Inledande metodgranskning – efterföljare till H-0013

2026-11-03. Granskad plan: f43c1e736a3312d10b28000f7feee38aca31d0e7. Detta är en granskning av metodförslag och återanvändningsgränser, inte ett godkännande av ny motorkod eller drift.

## Verifierat nuläge

- Arbetskopia /Users/edwinlyckoskold/Documents/GitHub/Trader_go, ren gren codex/h0013-research-plan på f43c1e7 vid start. Origin-grenen har samma revision. Origin/main är 72107ed; planen och de senare dokumentationscommitarna är inte mergade där.
- Registret har 16 olika hypotes-id, till H-0016. Momentummodellen är inte registrerad. H-0017 är endast ett möjligt nästa id och reserveras inte av detta dokument.
- H-0013-diagnosen reproducerades byteidentiskt från den hashverifierade sparade resultatfilen. Inga råarkiv eller strategier kördes.
- Fas 2-status: 40/40; Fas 3: 0/40; H-0016: 5/40 för dokumenterad förregistrering. Dessa är statusfiler på grenen, inte nya godkännanden av drift.
- Källkoden för den befintliga tjänsten, workerns H-0013-kontrakt och migration 0005 är granskad som återanvändningsunderlag. De tillåter inte att den nya modellen körs under H-0013:s id.
- Ingen SSH-session eller databasanslutning har öppnats i denna granskning. Dagens worker-PID, köstatus, faktiska migrationer och backupdatum är därför inte omverifierade. Tidigare driftuppgifter får inte beskrivas som aktuella mätningar.

## Fynd som måste vara lösta innan metodfrysning

| Id | Prioritet | Underlag | Problem och konkret krav |
|---|---|---|---|
| M01 | P1 | forskningsplan §4 | Funding och köp/sälj kan ha samma tidsstämpel. Ordningsval kan ge gratis undvikande av funding. Lås händelseordning och ett separat ordningskänslighetsprov. Anta inte att börsens avräkning är exakt samma som vår diskreta klocka. |
| M02 | P1 | forskningsplan §4, backtest.py | Vikt, handelsband och antal enheter saknar exakt mättid och avgiftsbas. Ett mål 100 % före avgift kan bli över 100 % efter avgift. Lås beslutstid, mekanisk fyllningsstorlek och redovisa avgift bara en gång. |
| M03 | P1 | forskningsplan §5 | Intrastapel-drawdown och mark-price behöver en exakt konservativ definition. OHLC avslöjar inte high/low-ordning. En antagen prisväg får inte presenteras som observerad. Marginal- och likvidationsmodellen är ännu inte låst. |
| M04 | P1 | forskningsplan §6 | Jämförelsernas short, ATR-stop, kapitalbas, självständiga riskstopp och ombalansering är inte helt specificerade. Upprätta en explicit jämförelsematris och bevisa att nya 1/3-blandningen inte är huvudmodellen i förklädnad. |
| M05 | P1 | forskningsplan §6 | Första beslut, sista fyllning, terminal funding och riskstopp vid UTC-midnatt saknar gemensam ordning. Lås hela horisonten och förhindra att 2025 används ens för sista öppningen. |
| M06 | P2 | engine/traderlab/stats.py:91 | max_drawdown räknar bara på de värden den får och lägger inte själv till ursprungskapital. En ny adapter måste inkludera 100 000 före första kostnaden. Ändra inte den gamla statistikfunktionen så att frysta resultat räknas om. |
| M07 | P1 | engine/traderlab/risk.py och backtest.py | Befintligt risk_overlay använder bruttorörelser och befintlig motor använder öppningsbaserad kapitalredovisning och stapelaggregerad funding. De uppfyller inte automatiskt det nya mark-/nettobaserade kontraktet. Återanvänd rena delar, men visa kontraktsöverensstämmelse före återanvändning av utförandet. |
| M08 | P2 | registry.py och forskningsplan §6 | Försöksantal N, kontrollkörningar och DSR:s beroendeantaganden måste skiljas åt. Använd olika registrerade id enligt befintlig registerkod, inte antal resultatrader. Redovisa även tidigare parametersökningar utan att låtsas att de är oberoende. |

Fynden M01–M05 och M07 är metod-/integrationsblockerare, inte bevis för ett fel i H-0013:s redan frysta resultat. Kontraktsutkastet nedan ger ett sammanhängande föreslaget svar; Claude ska kontrollera det och färdigställa leverans A. Ingen rad får markeras slutgodkänd enbart för att ett förslag skrivits.

## Egna små kontrollprov

- Sparad H-0013-diagnos omräknad med review.py och jämförd med diagnostics.json: identisk.
- Endast syntetiska tal: max_drawdown([99,98]) ger −1,0101 %, medan startkapital 100 följt av samma kurva ger −2 %. Det verifierar att den nya redovisningen måste inkludera startpunkten.
- Avgiftsorakel när markpris=kontraktspris=100, kapital 100 000, mål 50 % och kostnad 0,0016: q=499,60031974420474, kostnad 79,93605115907276, nettokapital 99 920,06394884092, slutvikt 50 %. Naiv q=500 uppfyller inte samma efterkostnadsvikt.

Ingen ny strategiutvärdering eller backtest på marknadshistorik ingick.

## Primärkälla för händelsekontraktet

[Binances dokumentation om funding](https://www.binance.com/en/support/faq/detail/360033525031), kontrollerad 2026-11-03, beskriver fundingbelopp med markpris och kontraktsstorlek och varnar för att avräkningen inte har en garanterad exakt avslutningstid. Den uppdaterade sidan är inte ett bevis för alla historiska regler 2020–2024.

[Binances marknadsdatareferens](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data) beskriver separata funding- och mark-price-endpoints. Att en endpoint finns bevisar inte att vår fullständiga historik är tillgänglig eller korrekt. Inga priser hämtades.

## Beslut

**Klart för Claudes leverans A, inte för leverans B eller riktig körning.** Leverans A delas i A1 (komplett metodutkast och orakel till Codex, ingen registerrad) och A2 (registrering efter godkänd A1-revision). Marginalmodellens data/antaganden och DSR-redovisningen får inte lämnas som öppna TODO i ett protokoll som påstås vara fullständigt fryst.

## Kontroll av granskningsleveransen

- Alla fyra checklistgeneratorer (momentum, Fas 3, H-0016 och Fas 2) godkänner status och underlagsvägar med --check.
- Den separata momentumvyn renderar 2/40, exakt två verifierade bockar och åtta öppningsbara arbetsområden i befintlig DOM-testmiljö.
- Kontraktets styckvisa storleksformel verifierades med syntetiska köp/sälj-exempel, också när markpris skiljer sig från kontraktspris och vid målvikten 100 % efter avgift. Relativ viktavvikelse < 1e−12 i exemplen.
- git diff --check passerar. Ingen engine-, app-, migrations-, register- eller fryst resultatfil har ändrats. Dessa prov verifierar dokumentens orakel och status, inte en ännu oskriven strategimotor.
