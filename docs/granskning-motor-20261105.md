# Svar på granskningsfynden i tvärsnittsmotorn (2026-11-05)

Gäller fynden i [fas2-inledande-granskning-20261102.md](fas2-inledande-granskning-20261102.md) om
H-0014/H-0015, och samma kod i H-0018–H-0020. Rättat i commit `1d80174`.

| Fynd | Åtgärd | Test |
|---|---|---|
| P1: slutprovets arkiv öppnas före filtrering | `xsrun`, `xsbig` och `basis` skickar periodgränser till alla läsare. Arkiv från 2025 och framåt öppnas inte. | `engine/tests/test_holdout_guard.py`: slutprovsarkiven är oläsbara och skulle krascha om de öppnades. Testet fallerar på den gamla koden. |
| P1: kapitalet kan återuppstå efter konkurs | `portfolio.run`: kapital ≤ 0 är slutgiltigt; alla positioner stängs och inga nya tas. | `test_bankruptcy_is_absorbing` med granskningens exempel (short −1, priset fyrdubblas). |
| P1: saknad finansieringsränta blir gratis | `portfolio.funding_gaps` räknar hållna dagar utan avräkning; `xsrun` och `xsbig` avbryter om det finns några. | `test_funding_gaps_counts_held_days_without_settlement` |
| Nytt: ordningen vid lika ränta avgjordes av flyttalsbrus | `xs.funding_score` avrundas till 12 decimaler, så lika räntor ger lika poäng oberoende av historikens längd. | `test_funding_score_ties_do_not_depend_on_history_length`, som fallerar utan rättningen. |
| P2: avnotering stängs på senaste kända öppning | Inte åtgärdat. Kräver tidsstämplade avnoteringsbesked. | – |

## Påverkan på resultaten

- Inga slutprovsdata har ingått i någon beräkning. Arkiven öppnades men skars bort före beräkningen.
- Ingen körning nådde konkurs. Inga hållna dagar saknade finansieringsränta, varken i H-0014/H-0015 eller i H-0018/H-0019.
- H-0014, H-0018 och H-0020 får exakt samma siffror med den nya koden.
- H-0015 och H-0019 ändras något av den deterministiska ordningen: +76,9 % i stället för +75,3 %, och +80,3 % i stället för +76,6 %. Båda är fortfarande REJECT, och kontrollraderna står i registret.
