# Datakvalitet

Kontrollerat med `python -m traderlab check` (skillen `hamta-data`). Rådata i `data/raw/` committas inte,
se `MANIFEST.md`.

## Binance spot BTCUSDT 4h, 2020-01 till 2026-09

Kontrollerat 2026-11-01. 81 månadsfiler, alla mot Binances SHA-256-kontrollsummor.

- Rader: 14 789 av förväntade 14 790. Dubbletter, tidsordning, tidsjustering, OHLC, priser och volym: inga fel.
  Tidsstämplar i mikrosekunder från 2025 tolkade rätt.
- **1 saknad stapel:** 2020-02-19 12:00 UTC. Troligen ett avbrott hos Binance. **Inte ifylld.**
- **13 utstickare:** granskade och bedömda som **äkta marknadshändelser**, kvar i datan:

| Tid (UTC) | Rörelse | Trolig händelse |
|---|---|---|
| 2020-03-12 08:00 / 20:00 | −17,9 % / −20,5 % | Coronakraschen |
| 2020-03-16 04:00 / 12:00 | −9,2 % / +12,8 % | Efterskalv efter kraschen |
| 2020-05-10 00:00 | −9,6 % | Före halveringen |
| 2021-01-11 20:00 | +9,8 % | Återhämtning efter januarifallet |
| 2021-01-29 08:00 | +14,7 % | Musks Twitter-profil "#bitcoin" |
| 2021-02-08 12:00 | +10,9 % | Tesla köper Bitcoin |
| 2021-04-18 00:00 | −8,3 % | Helgkrasch |
| 2021-05-12 20:00 | −8,8 % | Tesla slutar ta emot Bitcoin |
| 2021-05-21 12:00 | −10,5 % | Kinas tillslag mot gruvdrift |
| 2021-09-07 12:00 | −8,4 % | El Salvador-dagen |
| 2021-12-04 04:00 | −9,1 % | Blixtkrasch |

- **Ej gjort:** jämförelse mot en andra källa. Bara `data.binance.vision` är öppen i miljön.
- **Överlevnad:** BTC är inte påverkad av överlevnadsbias i ett test på en enda tillgång.
