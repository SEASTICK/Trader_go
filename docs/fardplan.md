# TraderGO – målbild och färdplan

Målbild bekräftad av Edwin 2026-11-02: TraderGO ska på sikt kunna förvalta en portfölj med riktiga pengar, välja mellan verifierade strategier och själv besluta om köp, försäljning och att stå utanför marknaden inom uttryckligt fastställda riskgränser.

Detta är projektets riktning, inte ett beslut att aktivera livehandel. Nuvarande kod och arbetsregler gäller fortsatt: historik och papper, inga mäklarkopplingar, ingen riktig orderkod och ingen lagring av börsnycklar i appen. En framtida liveintegration kräver ett separat uttryckligt beslut enligt `CLAUDE.md` och pengar-grinden. Reglerna får inte kringgås med hänvisning till målbilden.

## Projektets faser

| Fas | Leverans | Grind innan nästa steg |
|---|---|---|
| 1. Strategy Research Engine | Historiska data, realistiska backtester och spårbara resultat | Reproducerbarhet och dokumenterad datakvalitet; varje strategi bedöms mot förregistrerade kriterier |
| 2. Adaptive Strategy Engine | Identifiera marknadsläge och utvärdera val av strategi eller platt läge | H-0013 prövas som en egen forskningshypotes. REJECT-kandidater blir inte godkända genom att ingå i den. Kodtest, forskningsbeslut och eventuell vidare validering hålls åtskilda |
| 3. Live Paper Trading | Kör godkänt och fryst beslutsflöde i realtid utan riktiga pengar | Jämför signaler, exekvering och kostnader med testantagandena; dokumentera avvikelser enligt forskningsgrindarna |
| 4. Multi-Market Engine och portföljrisk | Flera marknader, kapitalfördelning och samlad risk | Verifiera exponering, korrelation, koncentration och förlustgränser i hela pappersportföljen |
| 5. Begränsad livehandel | Separat granskad orderintegration med uttryckligt begränsat kapital | Ett nytt uttryckligt beslut av projektägarna enligt pengar-grinden; risklager, orderavstämning, stopp och återställning verifierade före aktivering |
| 6. Utvärderad automatisk drift | Portföljen kan välja strategi, storlek, köp, försäljning eller platt läge inom godkända gränser | Utökning kräver uppmätta resultat och fungerande drift från föregående steg; ingen automatisk höjning av risk eller kapital |

Faserna beskriver produktutvecklingen. Forskningsgrindarna för en enskild strategi finns separat i [vägen till avkastning](vagen-till-avkastning.md). Att en fas är färdig innebär inte att någon strategi har klarat sin grind eller är godkänd för riktiga pengar.

## Ansvar i den framtida portföljkedjan

1. **Marknadsdata** levererar validerade, tidsstämplade underlag. Saknad eller inaktuell data ska kunna stoppa nya affärer.
2. **Strategiväljaren** väljer en tillåten strategi eller platt läge och lämnar en avsikt om målposition.
3. **Portfölj- och risklagret** bestämmer tillåten storlek och får neka varje avsikt. Strategin får inte kringgå kapital-, exponerings- eller förlustgränser.
4. **Orderhanteringen** är en separat framtida integration. Den hanterar orderstatus, delavslut och återförsök utan dubbla affärer och stämmer av innehav och order mot handelsplatsen.
5. **Drift och användarkontroll** visar beslut och positioner, sparar en granskningsbar historik och ger möjlighet att stoppa nya affärer och återhämta systemet efter fel. Stoppbeteendet och hanteringen av öppna positioner ska vara uttryckligen definierade.

Pengarna ska i en framtida liveversion finnas hos den valda handelsplatsen eller mäklaren; appens portföljvy avspeglar det verkliga kontot. Insättningar och uttag ingår inte i det automatiska strategimandatet. Handelsplats, instrument, kapital och riskgränser är ännu inte beslutade.

## Aktuellt arbete

Fas 2 är slutgodkänd av Edwin 2026-11-03 (40/40), med dokumenterade begränsningar och verifierad Stable 0.1.23. H-0013 blev REJECT och går inte vidare till papper. Se [releaseverifieringen](fas2-release-verifiering-20261103.md).

Nästa produktfas är [Fas 3 – Live Paper Trading](fas3-checklista.md). Planering och tekniska SIM-prov kan förberedas. Ett riktigt fryst framåttest får börja först när en kandidat klarat forskningsgrindarna och har READY_FOR_PAPER; någon sådan kandidat är ännu inte godkänd. Fas 3-listans statuskälla är docs/fas3-status.json. Bocka endast av verifierade punkter med underlag och regenerera med scripts/render-fas3-checklist.py.

ML kan senare prövas som en separat förregistrerad forskningshypotes och jämföras med den enkla väljaren. ML är inget krav för slutmålet och ger inget undantag från validering eller riskgränser.

Målbilden ändrar inte frysta protokoll, resultat, REJECT-beslut eller den skyddade slutprovsperioden. Den ger inga löften om avkastning. Inga livefunktioner, kontokopplingar, driftlarm eller nya betaltjänster införs genom detta dokument.
