# H-0013: jämförelsekurvor i resultatet (F2-704)

Skrivet 2026-11-03, innan kurvorna lades till. `research/fas2-protokoll.md`, frysta resultat och beslutskriterierna
ändras inte. Kurvorna är redovisning och påverkar inget beslut.

| # | Fråga | Tolkning | Varför |
|---|---|---|---|
| J1 | Vilka kurvor? | H-0013 och de fem jämförelserna (köp och behåll, EMA / ADX-trend ensam, Bollinger / RSI ensam, likaviktad blandning, riskfilter). Alla är kapital med start 1,0 på den ihopsatta kapitalbasen. | Samma jämförelser som i `docs/fas2-utvardering-tolkningar.md` (U3–U6). |
| J2 | Samma tidpunkter? | Alla kurvor delar samma tidsaxel, alltså staplarna med avkastning i de sex testfönstren (U1). En kurva med andra tidpunkter avvisas av läsaren. | Jämförelsen ska vara på samma observationer. |
| J3 | Storlek? | Högst 1 500 punkter, med samma utvalda index för alla kurvor. Varje k:te stapel och alltid den sista, som `metrics.curves`. Antalet staplar före urvalet anges. | Resultatet sparas i Supabase och visas i appen. Fullständiga kurvor finns inte i paketet. |
| J4 | Spårbarhet? | Varje kurva har en källa (funktionen i `fas2_eval` som räknade den), antal staplar och SHA-256 av den fullständiga avkastningsserien före urvalet. Därtill utvärderingsversionen och datasetet. | Granskaren kan räkna om kurvan på samma data och jämföra hashen. |
| J5 | Var i resultatet? | `curves.comparisons` i resultatpaketet till Supabase (`{t, series, sources, points, bars}`). `curves.t` och `curves.equity` är oförändrade. | Kompatibilitet. Databasens kontrakt kräver bara att `curves` är ett objekt. |
| J6 | Äldre resultat? | Ett resultat utan `curves.comparisons`, eller med en kurva som saknas eller inte kan läsas, visas med den kurvan som saknad. Nyckeltalen visas som förut. Inget fylls i. | Krav i F2-704 och i granskningarna av PR #77. |
| J7 | Driftsatt worker? | Den driftsatta workern (`dee88eb`) levererar inte kurvorna. Ett resultat från den visas med kurvorna som saknade, tills en ny release har driftsatts efter granskning och beslut. | Ingen driftsättning ingår här. |
