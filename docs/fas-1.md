# Fas 1: Strategy Research Engine, kartläggning och status

## Aktuell verifierad status 2026-11-02

**Hela Fas 1 är inte klar.** Stable 0.1.17 innehåller molnkopplingen och de registrerade offline-resultaten.
Senaste data-/strategiauditen beskrivs i `docs/fas1-data-audit-20261102.md`;
molnverifieringen i `docs/research-cloud-setup.md`. Tabellen skiljer färdig
kärnfunktion från sådant som fortfarande saknar slutverifiering.

Verifieringen avser desktopkällan `153e422` (Stable 0.1.17) och serverkällan
`4d2ba56`. PR #59 och #61 mergades därefter och ingår inte i den publicerade
appen eller den driftsatta workern. Deras nya export/serverkod behöver separat
granskning. Det nya deployflödet 41441143904 hoppade över driftsättning eftersom
SERVER_HOST saknas. På dropleten verifierades fortfarande exakt en aktiv
TraderGO-worker, `tradergo-research-worker.service`.

| Del | Verifierat | Kvar före slutgodkännande |
|---|---|---|
| 1. Arkitektur | Frontend, Rust, Python, databas, återanvändning och separat worker kartlagda; molnmodulen implementerad | Ingen separat arkitekturblockerare |
| 2. Historik | Binance-källa, 1H/4H/1D-stöd; frysta fem år UM BTCUSDT 4H med funding, SHA256, full täckning och Supabase-återläsning; dubblettskydd | Spotluckan kvar; den äldre uppgiften om 43 feljusteringar kan inte reproduceras; tidig UM-warmup rättad och provad mot januari 2020; automatisk schemalagd serversynk återstår |
| 3. Strategier | Fyra versionerade strategier, parametrar, indikatorreferenser och signaltester; reproduktion med 1 120 parameterförsök | Ingen strategi är godkänd för papper; nya idéer kräver nya registreringar |
| 4. Backtest | Tester för nästa öppning, framtidsläckage, stop/TP/gap, kostnader/funding, affärslogg och reproducerbarhet; samma UM buy-and-hold | Oberoende mark-price-/likvidationsvalidering är inte gjord |
| 5. Nyckeltal | Motorns statistik, kurvor, affärer, månads-/regimresultat och auditmetadata | Registrerade Fas 1-resultat visas nu i Research Lab via explicit adapter; första historikritning provad i Mac-kandidat 0.1.15; slutpaketets manuella kontroll återstår |
| 6. Optimering | Registrerat protokoll, Optuna, walk-forward, kostnadsstress, stabilitet, osäkerhet och bevarade auditförsök | Slutprovet förblir låst; alla fyra är REJECT |
| 7. Research Lab | Medlemsinloggning och utforskningskö; ny registrerad offlinevy med jämförelse, kriterier, UM-candles/markörer, equity/drawdown, affärer, filter/sortering och walk-forward | Start av nya registrerade jobb från UI; Windows-GUI saknar testdator. Historikens synlighet/hela period rättad och webbtestad; slutpaketets Mac-kontroll avbruten av appverktygets anslutningsfel |
| 8. Molndrift | Supabase/RLS, riktig samtidighetskontroll, kö/lease/fencing, separat systemd-worker och recovery-test | Användaren bekräftar DO-backup 7 dagar och daglig Supabase-backup; isolerad forskningsdataåterställning provad. Leverantörsåterställning, larm och bredare belastningstest kvar |
| 9. Godkännande | 145 Python-tester och 52 frontendtester; webbvyn granskad i båda teman; isolerad återställning med identiska värden/RLS; tidigare Rust-/molnkontroller | Mac-uppdatering 0.1.12 → 0.1.14 och registrerad vy verifierade. Windows-GUI (användaren har bara Mac), manuellt Mac-slutprov (verktygsanslutning blockerad), tom marknadscanvas observerad även i 0.1.14, sista driftkontroller och dokumenterat Fas 1-godkännande kvar |

Ingen livehandel. Ingen strategi får gå vidare till papper på grund av denna
tekniska reproduktion. Äldre status nedan är historik och ersätts av tabellen ovan.
Senaste leverans: `docs/research-chart-viewport.md`, `docs/research-lab-registered.md` och `docs/research-backup-restore.md`.
Backupens leverantörspolicyer är användarbekräftade, inte API-verifierade.

## Ursprunglig kartläggning (bevarad)

Fas 1-planen jämförd med det som fanns, det som byggts och det som avviker. Våra regler i CLAUDE.md går före
planen där de krockar.

## 1. Arkitektur

| Del | Var | Status |
|---|---|---|
| Forskningsmotor (Python) | `engine/traderlab` | Fanns: data, kvalitetskontroll, backtest, statistik, register, ML med gallrad CV, papper |
| Skrivbordsapp (Tauri, React) | `app/` | Fanns: Research-rutor, Hypoteser, Status, Papper, Marknad (prisdiagram) |
| Insamling av marknadsdata i appen | `app/src-tauri/src/market` | Fanns (Edwin): BTCUSDT 4h, lokalt i SQLite |
| Supabase | – | Fanns inte. Byggs i steg D när kontot finns |
| Research Engine som separat modul | `engine/traderlab/{indicators,metrics,optimize,fas1}.py`, `strategies/rules.py` | Byggt. Befintliga funktioner är oförändrade (alla äldre tester går igenom) |

## 2. Historisk marknadsdata

| Punkt | Status |
|---|---|
| Börs-API för OHLCV | Fanns: Binance publika datafiler med kontrollsumma (`data/binance.py`), utan nycklar |
| BTC/USDT, minst 5 år 4H | Klart: spot 2017-08 till 2026-09 (9 år), terminer 2020-01 till 2026-09 |
| 1H, 4H, 1D | Hämtat. **Spot 1h har 43 staplar på fel tid 2017**: kvalitetskontrollen stoppar den tills det är utrett |
| Luckor, dubbletter, felstaplar | Fanns: `quality.py` (fel stoppar, varningar loggas) |
| Spara i Supabase | Steg D |
| Inkrementell synk, pågående vs stängd stapel | Fanns i appens insamlare. Servern får samma i steg D |

## 3. Strategier

Klart i `strategies/rules.py`: ett gemensamt gränssnitt (`StrategySpec` → `Signals` med mål, stop och take-profit),
versionerade (`namn@version#parameterhash`), konfigurerbara parametrar med sökrymd, long, short och platt, och
enhetstester. Fyra strategier: `ema_adx_trend`, `donchian_breakout`, `bb_rsi_reversion`, `squeeze_breakout`.
Indikatorerna (`indicators.py`) är verifierade mot biblioteket `ta`.

## 4. Backtest

| Punkt | Status |
|---|---|
| Stapelvis motor, ingen framtidsdata | Fanns. Varje strategi testas med `check_no_lookahead` |
| Marknadsorder, stop-loss, take-profit | Stop och take-profit är nya, med gap-hantering och stop före take-profit vid dubbelträff |
| Courtage, spread, slippage, funding, hävstång och likvidation | Fanns |
| Varje affär registreras | Ja, med orsak till utgång (signal, stop, take-profit, likvidation) |
| Jämförelse med köp-och-behåll, reproducerbarhet | Ja. Fast frö, och samma id ger samma resultat |

## 5. Nyckeltal

Klart i `metrics.py`: nettoavkastning, CAGR, Sharpe, Sortino, max drawdown, Calmar, profit factor, vinstandel,
förväntat värde per affär, snittvinst och snittförlust, drawdown-kurva, månadsresultat och resultat per
marknadsregim (trend upp eller ned × hög eller låg volatilitet, bara med data som var känd vid tillfället).
Allt sparas per körning.

## 6. Optimering och validering

Klart i `optimize.py` och `fas1.py` enligt `research/fas1-protokoll.md`: Optuna, walk-forward med växande fönster,
parameterstabilitet, ett orört slutprov och objektiva kriterier skrivna före körning.

**Avvikelse från planen:** strategierna rangordnas inte efter vilken som "vann" och väljs sedan. Med fyra
strategier och tusentals försök hittar man alltid en vinnare av slump. I stället bedöms varje strategi mot sina i
förväg registrerade krav, och t-kravet stiger med antalet försök. Rangordningen visas, men den är inget beslut.

## 7. Research Lab i appen

Steg E. **Avvikelse:** en körning som startas med egna parametrar i appen blir antingen en registrerad hypotes
eller märks `UTFORSKNING`. Utforskning räknas som försök och kan aldrig bli ett beslut. Det följer regel 2 (hypotesen
skrivs ned före resultatet).

## 8. Backend, Supabase och drift

Steg D: tabeller för staplar, strategier, körningar, affärer och resultat, en jobbkö, radskydd (RLS) och en worker
på DigitalOcean som deployas från GitHub. Kräver kontona och hemligheterna (se chatten), som aldrig hamnar i Git.

## 9. Test och godkännande

Motorn har enhetstester för data, kvalitet, indikatorer, stop och take-profit, kostnader, framtidsdata,
walk-forward och reproducerbarhet. Belastningstest görs i steg D.

**Ingen livehandel kan aktiveras i Fas 1:** det finns ingen order- eller nyckelkod, och appen är bara för papper
(CLAUDE.md).
