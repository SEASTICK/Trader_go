# Fas 1: dataaudit och teknisk reproduktion 2026-11-02

Datagranskningen och reproduktionen är genomförda. Detta är inte slutgodkännande
av hela Fas 1 och ger inget tillstånd till papper eller livehandel.

## Verifierat dataset

Binance USDⓈ-M BTCUSDT 4H, 2020-01-01 till exklusivt 2025-01-01:

- 10 962 av 10 962 förväntade stängda staplar.
- 0 luckor, dubbletter, ordningsfel, feljusteringar eller OHLC/pris/volymfel.
- 5 481 av 5 481 fundinghändelser; originaltider bevarade. Högst 47 ms efter
  respektive 8h-gräns. Ändliga tal verifierade.
- 120 originalarkiv verifierade mot Binances publicerade SHA256.
- Tolv utstickare jämförda med Coinbase BTC-USD spot, ingen borttagen.
  Alla hade samma rörelseriktning. Tre skiljer över två procentenheter:
  2020-03-12 08:00 (2,61), 2020-03-12 20:00 (4,08), 2021-04-18 00:00 (3,03).
  Detta är olika börser, instrument och noteringsvalutor; kontrollen bekräftar
  inte att varje enskilt terminspris är korrekt. Skillnaderna förblir flaggade.
- Inga källfiler från 2025 eller senare lästes i auditen. Utvecklingsperioden
  har använts tidigare och är inte ett nytt oberoende slutprov.

Dataset-id: `6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c`.
Fryst manifest med käll-URL:er, filhashar, normaliserade tabellhashar och
kvalitetsrapport finns i `data/audits/fas1-20261102/frozen-6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c.json`.

Hela serien har också lagrats i Supabase: 10 962 staplar och 5 481 fundingrader.
Samtliga värden och tidsstämplar återlästes exakt och dubblettinsättning gav
oförändrat dataset. Se `cloud-dataset-verification.json` i revisionsmappen.

## De tidigare dataproblemen

**Spot 4H:** stapeln 2020-02-19 12:00 UTC saknas också i Binances publika
spot-API. Kontroll av 1H visar ytterligare saknade timmar under avbrottet.
Termins-API:t har en verklig 4H-stapel vid den tiden. Ingen spotstapel har
konstruerats eller ersatts med terminsdata. Spotperioden är fortfarande inte
ett komplett femårsdataset. API-svaren sparas i revisionsmappen.

**Spot 1H år 2017:** alla fem publicerade månadsarkiv augusti–december hämtades
på nytt och kontrollsummerades. 3 277 rader, 0 feljusterade tider. Den gamla
uppgiften om 43 feljusterade staplar kunde inte reproduceras. Originalfilerna
bakom det tidigare påståendet finns inte i denna checkout; orsaken kan därför
inte fastställas. Detta godkänner inte alla gamla 1H-data: augusti och september
har saknade timmar, och augusti är en partiell introduktionsmånad.

**Terminsuppvärmning:** den generella molnworkern begär 600 staplar före
periodstart och kan då efterfråga saknade månadsarkiv från 2019. Detta är en
begränsning i den generella körvägen. Det ursprungliga registrerade Fas 1-
protokollet använder historik från januari 2020; första OOS-perioden börjar
2022 och har två års historik tillgänglig. Auditen använder exakt denna
avgränsning och ändrar inte uppvärmningsreglerna eller strategierna.

## Reproduktion av de fyra strategierna

Protokollet registrerades i commit `fd2e6c5` innan strategikörningen.
Källversion och runtimeversioner sparas i auditens `metadata.json`.
40 TPE-försök per optimering, sex walk-forward-fönster plus slutlig
utvecklingsoptimering, seed 0. Totalt 1 120 försök: 1 094 COMPLETE och 26 PRUNED.
Alla bevaras i `research/audits/reproduction-20261102T101526Z/trials.jsonl`.

| Hypotes / strategi | OOS netto | Sharpe | 2,5× kostnader | Stabilitet | Beslut |
|---|---:|---:|---:|---:|---|
| H-0009 EMA/ADX | −2,57 % | 0,19 | −17,24 % | 100 % | REJECT |
| H-0010 Donchian | +10,38 % | 0,26 | −20,34 % | 100 % | REJECT |
| H-0011 BB/RSI | −29,92 % | −0,56 | −54,22 % | 0 % | REJECT |
| H-0012 Squeeze | +115,44 % | 0,92 | +49,88 % | 100 % | REJECT |

Alla fyra har **identiska nyckeltal, exporterade kurvor och slutparametrar**
som sina ursprungliga resultatfiler. Varje OOS-kurva kördes dessutom om med
samma valda parametrar och jämfördes exakt. Squeeze klarar tre kriterier men
inte t-kravet. Tidigare beslut ändras inte. Orörda slutprovet kördes inte.

Bootstrapintervall, årsresultat, resultat utan bästa året, fulla affärsloggar,
fönster och jämförelse med ursprungsfilerna finns i samma auditkatalog.
Mark-price-data och likvidationsmodellens träffsäkerhet är inte verifierade
med ett separat dataset. BTC valdes i förväg; resultatet säger inget om andra
marknader och eliminerar inte urvals- eller överlevnadsproblematik.

## Reproducera

Återskapa råfilerna i en separat katalog från manifestets käll-URL:er, inklusive
`.CHECKSUM` för varje Binance-arkiv och Coinbase-svaren från `secondary_source`.
Behåll filnamnen i manifestet. Kopiera `futures-manifest.json` och
`secondary-source.json` från `data/audits/fas1-20261102/` till katalogen.
Installera `engine/requirements.txt` och använd den registrerade källversionen.

```sh
PYTHONPATH=engine python scripts/audit-fas1.py --data /path/to/audit --verify-only
PYTHONPATH=engine python scripts/audit-fas1.py --data /path/to/audit --dataset 6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c
```

Programmet verifierar varje råhash, källa, månadsgräns, kvalitet och funding
innan körning. En ren committad checkout krävs. Resultat skrivs i en ny
katalog; tidigare resultat skrivs aldrig över. Efter att ha sett resultaten
får denna procedur inte användas för att anpassa parametrar mot slutprovet.

## Verifiering och kvarvarande arbete

136 Python-tester passerade lokalt, inklusive oläsbara slutprovsarkiv som
bevisar att periodavgränsningen görs före filöppning. Binances hämtare sparar
nu kontrollsummefilen för nyhämtade arkiv.

För hela Fas 1 återstår bland annat komplett Research Lab-resultatflöde för
registrerade körningar, resterande gränssnittsvyer, driftbackup med provad
återställning, övervakning, belastnings-/omstartstest och faktisk kontroll i
den installerade Stable-appen. Molnworkerns tidigaste uppvärmningsperiod behöver
hanteras uttryckligt. Strategierna är inte godkända för papper.
