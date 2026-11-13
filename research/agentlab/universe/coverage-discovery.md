# Universums- och datatäckningsaudit (Binance USDⓈ-M, daglig)

Genererad av `python -m traderlab.agentlab universe-audit`. Arkivlista hämtad 2026-11-13T13:31Z från https://s3-ap-northeast-1.amazonaws.com/data.binance.vision (bucket listing, filnamn). Universums- och täckningsaudit, Binance USDⓈ-M, daglig. Filnamnslistan sträcker sig bara till 2024-12; 2025+ är aldrig öppnat. Ändrar inga experimentposter.

## 1. Vad arkivet visar (arter)

| Art | Symboler med arkiv före 2025 | Varav listade senast 2022-12 | Med finansieringsarkiv | Utan |
|---|---|---|---|---|
| delivery | 38 | 20 | 0 | 38 |
| other | 1 | 0 | 1 | 0 |
| perp_busd | 41 | 40 | 41 | 0 |
| perp_usdc | 27 | 0 | 27 | 0 |
| perp_usdt | 396 | 166 | 396 | 0 |
| settled | 4 | 3 | 0 | 4 |

**Perp eller leverans.** Leveranskontrakt (38 st) har inga finansieringsarkiv (0 undantag); alla USDT-perpar (396 st) har det (0 undantag). Av 32 utgångna leveranskontrakt med lokala data ligger sista stapeln på utgångsdatumet i namnet för 26 och högst 2 dagar efter för 32.
7 USDT-perpar har färre finansieringsmånader än stapelmånader (arkivhål i finansieringen): BNXUSDT, BTCSTUSDT, ICPUSDT, JUPUSDT, LENDUSDT, QTUMUSDT, TLMUSDT.

**Omfång.** Agentlab handlar bara USDT-perpar (`universe.in_scope`). BUSD- och USDC-perpar, `*SETTLED` (efterhandsnamn på avnoterade kontrakt) och övriga produkter (`ETHBTC`, `BTCUSD1` ...) ligger utanför och redovisas nedan som avgränsning, inte som täckning.

## 2. Månadsfiler: listade i arkivet mot lokalt (USDT-perpar, 1d-staplar)

| År | Listade symbolmånader | Lokalt | Saknas | Andel saknas | Stapelmånad utan finansieringsfil i arkivet |
|---|---|---|---|---|---|
| 2020 | 509 | 509 | 0 | 0.0 % | 2 (0.4 %) |
| 2021 | 1404 | 1404 | 0 | 0.0 % | 14 (1.0 %) |
| 2022 | 1758 | 1758 | 0 | 0.0 % | 30 (1.7 %) |
| 2023 | 2436 | 2436 | 0 | 0.0 % | 3 (0.1 %) |
| 2024 | 3599 | 3599 | 0 | 0.0 % | 1 (0.0 %) |

Utanför omfånget (andra arter) saknas medvetet 1132 av 1290 symbolmånader (83 symboler). BUSD/USDC-perpar listade senast 2022-12 vars underliggande saknar USDT-perp: 0 st.

## 3. Arkivhål på dagsnivå (inne i ett kontrakts liv)

| År | Symboldagar mellan första och sista stapel | Hål | Andel |
|---|---|---|---|
| 2020 | 14360 | 0 | 0.0 % |
| 2021 | 41683 | 0 | 0.0 % |
| 2022 | 53046 | 273 | 0.5 % |
| 2023 | 72598 | 50 | 0.1 % |
| 2024 | 107728 | 0 | 0.0 % |

52 symboler har minst ett hål. Hål fylls aldrig i: kontraktet är ohandlingsbart den dagen.

## 4. Universum R001-R004 kunde välja mot punkt-i-tid-universumet (top 30, ålder ≥ 90 dagar)

Gamla panelen: 119 symboler varav 34 leveranskontrakt. Nya panelen: 396 symboler (311 fler än den gamla).

| År | Platser (ny) | Gamla platser utanför korrekt universum | Andel | Platser den gamla panelen inte kunde välja | Andel | Gamla platser på leveranskontrakt |
|---|---|---|---|---|---|---|
| 2020 | 6651 | 429 | 7.1 % | 1079 | 16.2 % | 0 |
| 2021 | 10950 | 774 | 7.2 % | 942 | 8.6 % | 0 |
| 2022 | 10950 | 2160 | 19.7 % | 2160 | 19.7 % | 35 |
| 2023 | 10950 | 3904 | 35.7 % | 3904 | 35.7 % | 17 |
| 2024 | 10980 | 5438 | 49.5 % | 5438 | 49.5 % | 193 |

## 5. R001-R004: bruttoexponering utanför ett korrekt universum (exploratoriskt, oförändrat)

148 kandidater (140 riktiga). Över 1 % utanför: 112; över 5 %: 112; med någon exponering mot leveranskontrakt: 99. Högsta andel 63.3 %, medel 23.6 %.

Skäl (andel av total bruttoexponering): inte USDT-perp 0.6 %, finansiering okänd 0.1 %, bortrankad av kontrakt som panelen saknade 26.4 %.

| År | Bruttoexponering | Andel utanför | Varav leveranskontrakt | Positionsdagar | Utanför |
|---|---|---|---|---|---|
| 2020 | 29003 | 5.1 % | 0.0 % | 282648 | 6.1 % |
| 2021 | 41931 | 13.2 % | 0.1 % | 672780 | 16.9 % |
| 2022 | 44644 | 24.2 % | 0.2 % | 652873 | 29.1 % |
| 2023 | 49058 | 35.9 % | 0.3 % | 685674 | 40.7 % |
| 2024 | 47488 | 46.5 % | 2.1 % | 684080 | 51.8 % |

## 6. Kvarstående luckor som blockerar bekräftande påståenden

Perpar i arkivlistan (USDT, listade senast 2022-12) som saknas i panelen: **0**.

