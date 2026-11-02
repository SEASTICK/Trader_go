# Fas 2-protokoll: inlärd spelbok som väljer strategi efter marknadsläge (H-0013)

Skrivet 2026-11-02, **innan** fas 2-motorn finns och innan något körts på riktig data. Protokollet ändras inte
efter registreringen. En ändring blir ett nytt protokoll och en ny hypotes.

## Frågan

Ger det bättre riskjusterad avkastning att låta en förväg bestämd regel, tränad bara på data före varje
testfönster, välja strategi per marknadsläge än att köra en av strategierna hela tiden, en blandning av dem eller
köp-och-behåll?

Hela motorn prövas som **en** hypotes, H-0013. Att den kan välja mellan 81 spelböcker räknas i Deflated Sharpe,
inte som 81 registrerade id.

## Marknad, data och perioder

| Del | Val |
|---|---|
| Marknad | Binance USDⓈ-M BTCUSDT (terminer), 4h, med finansieringsränta |
| Dataset | Det frysta datasetet `6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c` (120 arkiv med kontrollsumma), se data/MANIFEST.md |
| Utvecklingsperiod | 2020-01-01 till 2024-12-31. Ingen data före 2020-01-01 används |
| Slutprov (holdout) | 2025-01-01 till 2026-09-30. Läses inte in i Fas 2 |
| Bedömning | Den ihopsatta kurvan utanför urvalet, 2022-01-01 till 2024-12-31 |
| Körning | Som registrerat jobb genom Supabase-kön och workern på DigitalOcean, inte lokalt mot riktig data |

## Marknadsläge

Samma etiketter som `metrics.regimes`: `upp/hög vol`, `upp/låg vol`, `ned/hög vol`, `ned/låg vol`, och `okänt`
när indikatorerna inte är fyllda.

1. **Rått läge per dag**, vid dagens stängning (UTC):
   - Trend: dagsstängningen mot sitt 200-dagarsmedel. Över är `upp`, annars `ned`.
   - Volatilitet: standardavvikelsen för 30 dagars dagsavkastning mot sin expanderande median (minst 60 dagar).
     Över medianen är `hög vol`, annars `låg vol`.
   - `okänt` tills både 200-dagarsmedlet och medianen finns, alltså ungefär till juli 2020.
2. **Hysteres:** ett nytt läge gäller först när det rått har hållit i 3 dagar i rad. `ned/hög vol` och `okänt`
   gäller direkt, från första dagen. Att lämna `ned/hög vol` för ett annat läge kräver också 3 dagar.
3. **Per stapel:** gårdagens stängda dag gäller för dagens staplar. Ingen stapel ser sin egen dag.

Lägen uppdateras bara en gång per dygn.

## Kandidater och spelbok

Tre val per läge, utan optimering:

- `ema_adx_trend` 1.0.0 med standardparametrar (fast 50, slow 200, adx_n 14, adx_min 20, atr_n 14, stop_atr 3,0)
- `bb_rsi_reversion` 1.0.0 med standardparametrar (bb_n 20, bb_k 2,0, rsi_n 14, rsi_low 30, atr_n 14, stop_atr 2,0)
- `platt` (ingen position)

En spelbok tilldelar ett val till vart och ett av de fyra lägena: 3⁴ = 81 möjliga spelböcker. `okänt` är
alltid platt. `strategies.rules.SPECS` ändras inte.

### Handelsregler i spelboken

- **Bara med trenden:** long tillåts bara i `upp`-lägen och short bara i `ned`-lägen. En signal mot trenden blir platt.
- **Lägesbyte:** när läget byts stängs positionen vid nästa stapels öppning.
- **Ingen affär följer med:** en affär som påbörjats under ett annat läge, eller med en annan vald kandidat,
  tas inte upp igen. I det nya läget får kandidaten bara **öppna en ny affär**, alltså när dess signal går från
  platt eller motsatt riktning till en tillåten riktning efter lägesbytet.
- Samma sak gäller när spelboken byts vid en fönstergräns och läget har fått en ny kandidat.
- Beslut på stängd stapel, fyllning vid nästa stapels öppning. Strategins ATR-stop sätts vid inträdet.

## Urvalsregel (bestämd nu, används per träningsfönster och läge)

För varje kandidat (ema_adx_trend, bb_rsi_reversion) och träningsfönster:

1. Kör kandidaten i alla fyra lägen med handelsreglerna ovan, från 2020-01-01 till fönstrets början.
2. För varje läge: ta dagsavkastningen efter kostnader och finansieringsränta, bara för dagar i läget.

Välj för läget den kandidat som har **bäst Sharpe** och som samtidigt har:

- minst **20 affärer inledda i läget**, och
- t (Newey-West, dagsavkastningen i läget) **> 0**.

Klarar ingen kandidat båda villkoren blir läget **platt**. Vid exakt lika Sharpe väljs `ema_adx_trend`.
Ingenting från testfönstret används.

## Walk-forward

| Del | Val |
|---|---|
| Träning | Växande fönster från 2020-01-01 |
| Testfönster | Ett halvår: 2022-01, 2022-07, 2023-01, 2023-07, 2024-01, 2024-07 (som Fas 1) |
| Varje testfönster | Indikatorer och lägen räknas från 2020-01-01. Positionen är platt vid fönstrets början, och bara affärer som inleds i fönstret räknas, som i Fas 1. |
| Ihopsättning | Testbitarna sätts ihop och bedöms 2022-01-01 till 2024-12-31 |
| Slutlig spelbok | Väljs med samma regel på hela utvecklingsperioden och fryses (för slutprov och papper) |

## Kostnader och storlek

- **Kostnader:** avgift 10 bp, spread 2 bp och slippage 5 bp per sida. Stresstest med 2,5 gånger kostnaderna.
- **Finansieringsränta** betalas eller tas emot.
- **Storlek:** hela kapitalet, ingen hävstång (1×), startkapital 100 000.

## Beslutskriterier

`MORE_RESEARCH` om **alla** gäller på perioden utanför urvalet, annars `REJECT`:

1. t (Newey-West, dagsavkastning) ≥ **2,67** (N = 13, `python -m traderlab krav 13`)
2. Avkastning med 2,5 gånger kostnaderna > 0
3. Sharpe > köp-och-behåll på samma terminer och period (med kostnader och finansieringsränta)
4. Sharpe > bästa ensamma kandidat
5. Sharpe > likaviktad blandning

Definitioner för jämförelserna, på samma period och med samma kostnader:

- **Ensam kandidat:** kandidaten med standardparametrar, long och short som strategin själv avgör, utan lägesfilter.
- **Likaviktad blandning:** hälften av kapitalet i varje kandidat (ensam, enligt ovan) från periodens början,
  utan ombalansering. Kurvan är medelvärdet av de två kurvorna.

Kriterierna 1–3 är spår A:s (research/tracks.md). 4 och 5 är skärpningar för just den här frågan: en motor som
väljer strategi ska slå de strategier den väljer mellan.

En hypotes med `MORE_RESEARCH` går vidare till slutprovet med frysta spelböcker. Först därefter kan den bli
`READY_FOR_PAPER`. Ingenting här säger något om framtida avkastning.

## Kontroller som rapporteras (påverkar inte beslutet)

- Köp-och-behåll, varje kandidat ensam och den likaviktade blandningen, med samma nyckeltal som H-0013.
- **Riskfilter:** ema_adx_trend ensam, men platt i `ned/hög vol`.
- **Permutationstest:** lägesetiketterna slumpas blockvis per dygn (varje dygns etikett flyttas som ett block),
  fast frö 0, 200 permutationer. Hela walk-forward, inklusive urvalet, körs om för varje permutation. Andelen
  permutationer med minst lika hög Sharpe utanför urvalet redovisas som p-värde.
- **Deflated Sharpe** med 81 försök (antalet möjliga spelböcker).
- Antal dagar och affärer per läge, i varje träningsfönster och utanför urvalet, och vald spelbok per fönster.
- **Slumpkontroll** (`experiment.random_label_control`), som för tidigare hypoteser.
- Max nedgång, Sortino, Calmar, exponering, omsättning, resultat per år och resultat utan bästa året.

## Kända svagheter, skrivna i förväg

- **Delvis hittad efter att ha sett resultat.** BTC 2020–2024 är sedd i H-0001 till H-0012, och Fas 1:s
  regimresultat är sedda. Idén att välja strategi efter läge är vald efter de resultaten.
- **Få episoder i `ned/hög vol`.** Urvalet där kan bero på ett fåtal perioder, så regeln faller ofta tillbaka
  på platt. Kravet på 20 affärer är till för det.
- **Lägen uppdateras bara dagligen**, och med hysteres på 3 dagar. Snabba vändningar fångas sent.
- **Kandidaterna är REJECT ensamma i Fas 1**, med optimerade parametrar. Här används standardparametrar.
- **Stop-loss** antas fyllas på stopnivån eller på öppningen vid gap. Verklig glidning vid kraftiga rörelser kan
  vara större. Separat mark-price och likvidation verifieras inte i Fas 2.
- **Den likaviktade blandningen** ombalanseras inte. Det är en förenkling.
