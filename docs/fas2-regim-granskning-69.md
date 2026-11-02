# Regimmodul H-0013 – granskning av PR #69

Granskad kod: `c27a9e020fb68af0a04f2011ce241d1f84a69b15`, gren `fas2-regim`, bas `3c2465b`.
PR: https://github.com/SEASTICK/Trader_go/pull/69. Status vid granskning: öppen, inte mergad, driftsatt eller publicerad.

## Verifierat

- Isolerad kopia av exakt PR-commit: samtliga 206 Python-tester passerar, inklusive de 19 regimtestfallen.
- PR:ens Engine check passerar även i GitHub Actions.
- Trend 200 dagar, volatilitet 30 dagar, expanderande median med minst 60 värden och etiketter följer protokollet på kompletta, korrekt tidsstämplade serier.
- 4H-staplar använder föregående stängda dags läge på den verifierade regelbundna tidsaxeln. Prefix- och prisperturbationstester passerar.
- Ordinarie hysteres och omedelbart `ned/hög vol`/`okänt` fungerar på sammanhängande dagserier.
- Endast `regime.py` och `test_regime.py` har ändrats i PR:en. Inga ändringar av frysta strategier, protokoll, resultat, migrationer eller drift.

## Öppna fynd före godkännande

1. **P2 – tre rader räknas som tre dagar även när kalenderdagar saknas.** `engine/traderlab/regime.py:66–75`, `with_hysteresis`, räknar konsekutiva värden utan att validera dagsindexets kontinuitet. Oberoende syntetiskt prov med samma upp-läge 1, 3 och 4 januari ger `okänt, okänt, upp/låg vol`: läget bekräftas trots att det bara funnits två kalenderdagar i rad. `daily_closes` kan utelämna ofullständiga dagar, så detta kan uppstå även via modulens normala anrop. Kräv kompletta dagserier eller hantera luckan uttryckligt utan att bära bekräftelser över den. Lägg regressionstest för saknad dag och ofullständig dag mitt i serien.

2. **P2 – 4H-inmatningens tidsram och justering valideras inte.** `engine/traderlab/regime.py:36–49`, `_step`/`daily_closes`, drar slutsats om tidsram från hela indexets median och använder `>=` för dygnsslut. Samtliga tider förskjutna 30 minuter accepterades i ett oberoende prov och gav 300 dagsvärden. Det är inte protokollets UTC-justerade 4H-serie. Validera tillåtna tidsramar, tidsjustering och fullständiga dygn; undvik att framtida tidsstämplar avgör hur tidigare staplar tolkas. Lägg tester för feljustering och gles/oregelbunden serie. Om en funktion med tillförda dagslägen medvetet har ett friare kontrakt ska det framgå separat.

Proverna ovan använder enbart syntetisk data. Ingen verklig forskningskörning, optimering eller läsning av slutprovet har gjorts.

## Checklista

F2-201 och F2-203 är verifierade i PR-committen och får markeras klara med denna avgränsning. F2-202, F2-204 och F2-205 kvarstår tills luckhantering/tidsvalidering är rättad och granskad. Mergad kod, worker, Supabase och appintegration är separata steg och är inte klara genom detta deltest.

Nästa steg: rätta de två fynden i PR #69, kör relevanta tester, ange ny commit och uppdatera `docs/fas2-status.json`. Återanvänd H-0013:s registrerade parametrar och kör inga nya försök på verklig data i denna leverans.

## Omgranskning av 949c44a (kodrättning 496d8aa)

Exakt granskad PR-head: `949c44acc2ee01a99acdd47a9997cdbf05725c75`. Båda tidigare fynden är rättade: kalenderluckan nollställer hysteresen, och UTC-justering/tidsram valideras uttryckligt utan medianinferens. En isolerad körning av hela Python-sviten gav **223 passerade tester**, inklusive **36 regimtestfall**. De två tidigare oberoende reproduktionsproven passerar nu också.

F2-201, F2-202 och F2-203 är verifierade på denna kodversion. Den strikta kalenderhanteringen med cirka 200 kompletta dagars ny uppvärmning efter en lucka kan behållas: inget pris imputeras och protokollets parametrar ändras inte. En glest samplad serie som fortfarande ligger på 4H-rutnätet kan inte alltid skiljas från saknade staplar utan ytterligare metadata; att den ger `okänt` är en redovisad begränsning, inte ett påstående om komplett data.

### Kvarvarande P2: `current()` kan ge ett gammalt läge efter en lucka vid seriens slut

I `engine/traderlab/regime.py:130–133` returneras fortfarande sista värdet i `daily(bars)`. Kalendern där slutar vid den senast kompletta dagen. Om dagen efter den är ofullständig/saknas och det finns enstaka staplar från nästa dag, utelämnas luckan i svansen. Då kan `current()` ge ett gammalt handelsläge trots att rätt läge för nästa stapel är `okänt`. `per_bar()` har redan korrekt exakt uppslag och är inte drabbat av detta prov.

Oberoende syntetiskt reproducerat på 400 dygn, 4H, `make_bars(..., seed=7, vol=.02)`: ta bort hela näst sista dygnet och behåll bara 00:00-stapeln på sista dygnet. Resultat:

- Sista observerade stapel: 2021-02-03 00:00 UTC.
- Föregående kalenderdag: 2021-02-02, saknad.
- `per_bar(bars).iloc[-1]`: `okänt`.
- `current(bars)`: `ned/låg vol` från 2021-02-01.
- Nästa 4H-stapel ligger fortfarande 2021-02-03 och ska också ha `okänt`.

Rätta `current()` så att den använder exakt föregående kalenderdag för den **nästa stapeln**, utifrån uttrycklig tidsram, och returnerar `okänt` när den dagen inte är komplett. Återställ en tydlig beskrivning av detta kontrakt. Regressionstesta saknad och ofullständig föregående dag nära seriens slut, liksom en vanlig påbörjad sista dag och en komplett sista dag. Ett bra kontrakt är att `current(bars)` alltid matchar `per_bar(next_bar, daily(bars), interval)` på samma indataserie.

**Bedömning:** de två ursprungliga fynden är åtgärdade. F2-204 och F2-205 lämnas öppna tills kantfallet ovan har rättats och verifierats. PR:en är inte mergad, ingen riktig data har körts och inget är driftsatt eller publicerat i denna granskning. Strategiväljaren bör vänta på denna sista rättning.

## Slutgranskning av 866d393 – godkänd för merge

Granskad PR-head: `866d3935b2895437df82e8ce7987fe602b21bac3`, kodrättning `ebc5d38`. `current()` validerar nu angiven tidsram, beräknar nästa stapel och slår upp exakt föregående kalenderdag. Tom data ger `okänt`. Det äldre läget förs inte över en lucka.

Verifiering utförd oberoende på en isolerad kopia av exakt PR-head:

- Hela Python-sviten: **253 passerade testfall**, inklusive **66 regimtestfall**.
- Det tidigare syntetiska felprovet med saknad näst sista dag och bara 00:00 på sista dagen ger nu `okänt`.
- Kontraktet `current(bars, interval) == per_bar(next_bar, daily(bars, interval), interval)` passerar också oberoende kontroller för 1h, 4h och 1d, med dagsgränser och lucka.
- Kodändringen sedan föregående granskning är begränsad till `current()` och dess tester; kalenderhysteres, tidsvalidering och strikt uppvärmning är bevarade.

**Beslut:** samtliga tre granskningsfynd är åtgärdade. Regimmodulen godkänns för merge på den granskade kodversionen. F2-201–F2-205 är verifierade. Detta är kodgodkännande, inte driftsättning, ett resultat från riktig data eller ett godkännande för paper/live. PR:en är fortfarande öppen vid granskningen och inga sådana steg har utförts här.

Nästa avgränsade leverans är strategiväljaren (F2-301–F2-305), med syntetiska tester för trendriktning, platt läge, kandidat-/lägesbyte och nästa öppning. Inga nya optimeringar eller läsningar av slutprovet behövs för den leveransen.
