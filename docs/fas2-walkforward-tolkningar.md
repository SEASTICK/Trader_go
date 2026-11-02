# H-0013: tolkningar för urvalsregel och walk-forward

Skrivet 2026-11-02, innan träningsregeln och walk-forward implementerades och innan något körts på riktig
data. `research/fas2-protokoll.md` ändras inte. Där protokollet inte säger exakt hur något räknas står frågan
här, tillsammans med den tolkning koden använder. En annan tolkning blir en ny hypotes, inte en ändring av H-0013.

| # | Fråga | Tolkning i koden | Varför |
|---|---|---|---|
| 1 | Hur körs en kandidat "i alla fyra lägen med handelsreglerna" i träningen? | Spelboken som väljer kandidaten i alla fyra lägen, genom strategiväljaren (`adaptive.signals`) och `backtest.run`. Det betyder trendfilter, platt vid `okänt`, stängning vid lägesbyte och nya inträden bara efter byte. Kostnader och finansieringsränta ingår. | Protokollets steg 1 under Urvalsregel. Samma regler som i testet. |
| 2 | Vilka dagar hör till ett läge? | Dagarna vars staplar styrs av läget, alltså `regime.per_bar` (gällande läge för dagen före). Dagsavkastningen är `stats.daily_returns` för den dagen. | Hela dagen styrs av samma läge. Kostnaden för att stänga vid ett lägesbyte, vid 00:00-öppningen, hamnar på den nya dagen. |
| 3 | När räknas en affär som inledd i ett läge? | När läget för stapeln där affären fylls är läget. Det är samma läge som beslutet vid föregående stängning använde. | Beslut på stängd stapel, fyllning vid nästa öppning. |
| 4 | Sharpe och t? | `stats.sharpe` (365 dagar per år) och `stats.newey_west_t` på dagsavkastningarna i läget, som i Fas 1. Ett läge utan avkastning eller utan spridning ger t ≤ 0 eller saknat t. Kandidaten blir då ovalbar. | Samma mått som protokollets beslutskriterier. |
| 5 | Krav och lika Sharpe? | Minst 20 inledda affärer och t > 0, strikt. Bland valbara: högst Sharpe. Vid exakt lika Sharpe (samma flyttal) väljs `ema_adx_trend`. Annars platt. | Ordagrant protokollet. |
| 6 | Träningsperiod? | Staplar från 2020-01-01 till fönstrets början, exklusivt. Läget och indikatorerna värms upp inom samma period. | "från 2020-01-01 till fönstrets början". |
| 7 | Hur startar ett testfönster? | Staplar från 2020-01-01 till fönstrets slut läses för indikatorer och lägen. Spelboken börjar gälla vid fönstrets första stapel. Före den är positionen platt. Kandidaten måste ge en ny inträdessignal efter starten och får inte ta över en signal som redan pågick. | Protokollet: platt vid fönstrets början, bara affärer som inleds i fönstret, och spelboksbyte vid fönstergräns behandlas som lägesbyte. Det är striktare än Fas 1, som kunde fylla en pågående signal vid fönstrets första öppning. |
| 8 | Vad händer vid fönstrets slut? | Positionen stängs senast vid öppningen av fönstrets näst sista stapel, med kostnad, och är platt därefter. Backtestmotorn räknar avkastning från öppning till nästa öppning. Den sista stapelns rörelse skulle därför kräva nästa fönsters, eller slutprovets, första öppning, och den rörelsen räknas inte. | Protokollet säger inget. Fas 1 lät positionen ligga kvar utan stängningskostnad. Att stänga inom fönstret räknar varje kostnad exakt en gång och läser aldrig slutprovet. |
| 9 | Ihopsättning? | Varje fönsters avkastning per stapel, bara stapeltider inom fönstret. Fönstren överlappar inte. Kostnad och finansieringsränta summeras per fönster, och affärer räknas bara om de inleds i fönstret. | Ingen dubbelräkning. |
| 10 | Slutlig spelbok? | Samma urvalsregel på hela utvecklingsperioden, 2020-01-01 till 2025-01-01 exklusivt, versionsmärkt med kontraktet `h0013-adaptive/1.0.0` och spelbokens id. | Protokollet: väljs med samma regel och fryses. |
| 11 | Slutprovet? | Indata med stapel eller finansieringsränta från 2025-01-01 eller senare avvisas innan något räknas. Inläsningen från arkiven begränsas till före 2025-01-01, så arkiven för slutprovet öppnas aldrig. | Protokollet: slutprovet läses inte i Fas 2. |

Granskaren avgör om tolkningarna godtas innan någon riktig körning görs.
