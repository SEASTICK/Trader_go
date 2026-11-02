# Urvalsregel och walk-forward H-0013 – granskning av PR #71

Granskad PR-head: `74d46e31b434e5d2d9f57b71f6762c93eb9d7073`, kod `80d8847`, gren `fas2-walkforward`, bas `bcb14c9`.
PR: https://github.com/SEASTICK/Trader_go/pull/71. Bara syntetiska data har använts. Ingen merge, driftsättning, publicering eller läsning av verkligt slutprov har gjorts i granskningen.

## Fynd före merge

### P1 – direkta beräkningsanrop kan kringgå slutprovsskyddet

`engine/traderlab/fas2.py:101–107` (`train`) och `:115–131` (`evaluate_window`) saknar den utvecklingskontroll som finns i `walk_forward` och `load_development`. `train(..., end="2025-01-03")` accepterar staplar och funding från januari 2025 och skickar dem till kandidatberäkningen. `evaluate_window(..., start="2025-01-01", end="2025-01-03")` accepterar också denna period och beräknar ett resultat.

Detta reproducerades med syntetiska 4H-staplar 2025-01-01–2025-01-02 och motsvarande funding. En spion på kandidatberäkningen i `train` såg staplar till 2025-01-02 20:00 och funding till 16:00. Ett separat direktanrop till `evaluate_window` med en platt spelbok returnerade testperioden 2025-01-01–2025-01-03. Huvudflödets skydd fungerar; felet är att andra publika ingångar kan kringgå det.

Rätta med gemensam kontroll före beräkning i de publika dataingångarna, även `regime_stats`, och validera periodparametrarna: start/slut måste ligga inom tillåten utvecklingsperiod och vara korrekt ordnade. Regressionstesta varje ingång direkt med förbjudna staplar, förbjuden funding och otillåtna periodgränser. Bevisa att regim-, kandidat- och backtestberäkning inte anropas vid avvisning. Behåll arkivbegränsningen före filöppning.

### P2 – ihopsatt kapital och rapporterade belopp använder olika kapitalbaser

`engine/traderlab/fas2.py:173–181` räknar ränta på ränta via fönstrens avkastning, men summerar kostnader, funding och affärsobjekt från separata körningar som var och en startar med kapital 1. Beloppen skalas inte med det kapital som finns vid nästa fönsters början. Därmed kan affärsloggen och totalbeloppen inte stämmas av mot den ihopsatta kapitalkurvan.

Oberoende, kontrollerat syntetiskt prov med sex fönster, vart och ett med nettoavkastning +100 %, kostnad 0,01 och funding 0,02 på lokalt startkapital 1:

| Mått | Nuvarande resultat | Gemensam kapitalbas med start 1 |
|---|---:|---:|
| Slutkapital | 64 | 64 |
| Total kostnad | 0,06 | 0,63 |
| Total funding | 0,12 | 1,26 |
| Summa affärernas nettopnl | 6 | 63 |

Provet ersätter tränings-/fönsterfunktionerna med deterministiska resultat för att isolera ihopsättningen; det är ingen ny strategikörning. Nuvarande enhetstester jämför ojusterade summor med varandra och kan därför inte upptäcka problemet.

Rätta redovisningen till en gemensam kapitalbas. Skala fönstrens belopp och kopior av affärsloggen med ingående kapital och redovisa kapitalbasen uttryckligt. Prisnivåer och positionsandelar ska inte skalas. Lokala normaliserade fönstervärden kan sparas separat med tydliga enheter. Lägg regressioner med olika avkastning mellan fönster och kontrollera affärernas nettosumma mot slutkapital minus startkapital, samt kostnader och funding på samma bas.

## Verifierat

- Isolerad körning av exakt PR-head: **369 Python-testfall passerar**, inklusive **42 nya fas2-testfall**.
- Urvalsgränserna 19/20/21 affärer, strikt positivt t, högst Sharpe, EMA vid exakt lika Sharpe och platt utan valbar kandidat passerar granskning och tester.
- Ordinarie `walk_forward` använder sex rätt ordnade halvårsfönster och tränar på historik före varje fönster. Ändrade framtida värden ändrar inte tidigare spelböcker i testerna.
- `load_development` begränsar arkivvalet till före 2025 innan inläsning. Huvudflödet avvisar förbjudna indata före träning.
- Versionsmärkning av slutlig spelbok och deterministisk återkörning är verifierade. Ingen Optuna eller annan parameteroptimering har tillkommit.
- PR #70 är mergad som `bcb14c9`; strategiväljaren och dess tester är oförändrade jämfört med godkänd `db54bbe`.

## Bedömning av tolkningarna

Tolkningarna skrevs före implementationen. Exakt dags-/inträdesattribution och den dokumenterade platta fönsterstarten kan behållas. Ingen gammal affär tas över. Att bokföra utträdeskostnad på den nya dagen är en uttrycklig begränsning i den villkorade träningsstatistiken, inte en separat vinst i det nya läget.

Den tvingade stängningen vid näst sista öppningen och utelämnad sista rörelse är en redovisad exekveringskonvention för denna implementation. Den är inte garanterat mer försiktig i avkastning: tidig stängning kan både förbättra och försämra ett utfall. Behåll spårbar version och dokumentera den när jämförelserna i arbetsområde 5 byggs, så att samma underliggande observationsperiod och uttalade exekveringsantaganden används. Inget slutprov får öppnas för att få en extra slutkurs. Det frysta protokollet och äldre resultat ska inte skrivas om.

Den syntetiska fullkörningen med verklig urvalsregel blir oftast platt. Det är inte ett godkänt strategiresultat. Utöver befintliga separata tester behövs en kontrollerad, icke-platt sammansatt regression för kapitalredovisningen ovan. Riktiga forskningsdata behövs inte för att rätta fynden.

## Checklista och beslut

F2-402 (urvalsgränser och platt/tie-break) och F2-405 (versionsmärkning och reproducerbarhet) är verifierade på denna PR-head. F2-401 och F2-403 lämnas öppna för period-/slutprovsskyddet, F2-404 för kapitalredovisningen. Gemensam status: **17/40 verifierade**.

PR #71 är ännu inte godkänd för merge. Nästa kontroll är rättade direkta dataingångar och en avstämd kapital-/affärsredovisning, med syntetiska regressioner och uppdaterad checklista.
