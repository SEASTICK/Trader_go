# H-0024 datapreflight: UPPFYLLT

Bara täckning enligt protokollets datakrav. Inga kurser, ingen avkastning, ingen Sharpe, inget t-värde, ingen placebo och inget beslut. Slutprovet (2025-01-01 och senare) är inte läst: förfrågan slutar vid 2025-01-01 (exklusivt), serien kapas före första kontroll (0 rader kapades).

Källa: Yahoo chart-API (SPY); hämtad 2026-11-14T15:18:41Z. Rader i primärperioden 2006-01-01..2024-12-31: 4781. Serie-SHA-256 (justerad öppning och stängning, 6 decimaler): `17b4029d522651331a272cac8685893b6b1fa9362ff2fb789e64a2e2977cfde0`.

## Krav

| Krav | Utfall |
|---|---|
| 1. Justerad öppning och stängning för alla NYSE-sessioner, inga saknade värden, inga extra dagar | uppfyllt |
| 1b. 249–253 handelsdagar per kalenderår | uppfyllt |
| 2. Minst 15 handelsdagar per kalendermånad | uppfyllt |
| 2b. Varje T0–T3-cykel har sina fyra fönsterdagar plus T4 | uppfyllt |
| 3. Inget från 2025-01-01 eller senare används | uppfyllt |
| **Hela datakravet** | uppfyllt |

Saknade NYSE-sessioner: 0
Dagar som inte är NYSE-sessioner: 0
Rader med saknade fält: 0
Månader under 15 dagar: 0
Cykler: 227 av 227 kompletta

Handelsdagar per år: 2006: 251, 2007: 251, 2008: 253, 2009: 252, 2010: 252, 2011: 252, 2012: 250, 2013: 252, 2014: 252, 2015: 252, 2016: 252, 2017: 251, 2018: 251, 2019: 252, 2020: 253, 2021: 252, 2022: 251, 2023: 250, 2024: 252

NYSE-kalenderns verifiering: 176 av 176 stängningar belagda (maskinavstämning).

H-0024 är inte körd. Ingen registerrad skrivs i den här PR:en.
