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
