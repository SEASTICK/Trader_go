# H-0030: känslighetsgrid för H-0027–H-0029 (andra tidsramar och inställningar)

Skrivet och registrerat 2026-11-14, **efter** att H-0027, H-0028 och H-0029 körts och fått REJECT, och **innan**
någon variant nedan körts eller kodats. Edwin bad uttryckligen om fler tidsramar och inställningar. Gridet är helt
bestämt här; inga varianter läggs till eller tas bort efter resultat.

## Varför det här är ett eget, strängare försök

Att pröva många varianter av en idé är det lättaste sättet att lura sig själv. Därför:

- **Alla 50 varianter räknas.** Kravet på t för den bästa varianten räknas med N = 29 + 50 = 79:
  Φ⁻¹(1 − 0,05/79) = 3,2236, avrundat uppåt till **3,23**. Det är kravet för varje variant. Varianterna
  får fasta id (H-0030-R01 … R27, O01 … O14, M01 … M09 i den ordning de står nedan), och kommande försök ska räkna
  H-0030 som 50 försök, inte ett.
- **Ingen variant kan bli godkänd här.** Klarar en variant alla fyra kriterier i research/intradag-protokoll.md med
  t ≥ 3,23 blir H-0030 `MORE_RESEARCH` för just den varianten, och nästa steg är en ny registrerad hypotes som
  bara prövas på slutprovet 2025-01 till 2026-09 efter Edwins beslut. Annars REJECT.
- Idéerna kommer från H-0027–H-0029, vars resultat redan har setts. Gridet innehåller inga varianter som valts
  efter de resultaten: framför allt prövas **inte** omvänt tecken i H-0029, även om dess t var negativt.

## Gemensamt

Samma som research/intradag-protokoll.md: Binance USDⓈ-M BTCUSDT, 2020-01-01 till 2024-12-31 UTC, beslut vid stängd
stapel och fyllning vid nästa öppning, 1×, 6,05 bp per sida plus funding, stress 2,5 gånger, spår B, samma fyra
kriterier, samma regler för dygn, saknade staplar, periodens slut (sista öppning 2024-12-31 23:00 för 1h, 23:45 för
15m, 23:55 för 5m) och slumpkontroll. Slutprovet hämtas inte.

## Gridet (50 varianter)

### Familj R: reversering efter extrem stapel (från H-0027), 27 varianter

- Tidsram: 5m, 15m, 1h.
- Tröskel k: 2,5, 3, 4 (gånger standardavvikelsen).
- Hålltid: 1, 3, 6 timmar (alltså 12/36/72 staplar på 5m, 4/12/24 på 15m, 1/3/6 på 1h).
- Fönster för standardavvikelsen: alltid 30 dygn av föregående staplar (8 640 på 5m, 2 880 på 15m, 720 på 1h),
  ddof = 1, utan lucka.
- r_t = close_t / close_{t−1} − 1 över en sammanhängande stapel. σ_t räknas på de W föregående avkastningarna
  (inte r_t) och kräver W + 1 sammanhängande föregående staplar.
- I övrigt som H-0027: första extrema stapeln per UTC-dygn, mot rörelsen. Hålltiden räknas från inträdet (öppningen
  efter signalstapeln); utträde vid inträde + hålltid eller vid nästa 00:00 UTC, det som kommer först. Ingen affär om
  inträde och utträde blir samma öppning.
- Ordning för id: tidsram 5m, 15m, 1h; inom den k 2,5, 3, 4; inom den hålltid 1, 3, 6 timmar (R01 = 5m, 2,5, 1 h).
- Varianten 1h, k = 3, 3 timmar är identisk med H-0027 och körs igen som kontroll (ska ge samma resultat).

### Familj O: utbrott ur USA-öppningens intervall (från H-0028), 14 varianter

- Tidsram: 5m, 15m, 1h.
- 5m och 15m: intervallet börjar 09:30 New York-tid och är 30, 60 eller 120 minuter långt.
- 1h: staplarna öppnar på hel timme, så intervallet är stapeln som öppnar 10:00 (60 minuter) och signalen kan
  bara komma i stapeln som öppnar 11:00. Ett intervall på 120 minuter skulle sluta 12:00 och lämna inget
  signalfönster, så det ingår inte.
- Utträde: 13:00 eller 16:00 New York-tid.
- Signalfönster: staplar som öppnar på eller efter intervallets slut och stänger senast 12:00 New York-tid. Signal är
  den första stängningen strikt över intervallets high (long) eller strikt under dess low (short). Alla
  intervallstaplar måste finnas. Bara måndag till fredag.
- Inträde vid nästa stapels öppning. Målet hålls till och med stapeln som slutar vid utträdestiden och är 0 i den
  stapel vars stängning är utträdestiden, så utträdet sker vid öppningen 13:00 respektive 16:00 New York-tid.
- 1h: intervall 10:00–11:00, signal i stapeln 11:00–12:00, inträde 12:00.
- Ordning för id: 5m (intervall 30, 60, 120; inom det utträde 13:00, 16:00), sedan 15m likadant, sedan 1h.
- Antal: 5m 3×2 = 6, 15m 3×2 = 6, 1h 1×2 = 2.
- Varianten 15m, 60 min, 16:00 är identisk med H-0028 och körs igen som kontroll.

### Familj M: tidiga timmar förutsäger sena (från H-0029), 9 varianter

- Tidsram 1h (finare staplar ger samma gränser och därmed samma signal).
- Tidigt fönster från 00:00 UTC: 3, 6 eller 12 timmar.
- Signal s = tecken(close för stapeln som öppnar h − 1 / open för stapeln 00:00 − 1), där h är fönstrets längd i
  timmar. Alla staplar i det tidiga fönstret måste finnas.
- Inträde 12:00, 18:00 eller 21:00 UTC: första målet sätts på stapeln före inträdet (öppnar 11:00, 17:00 eller
  20:00), sista på stapeln som öppnar 22:00, och målet är 0 i stapeln som öppnar 23:00, så utträdet sker 00:00 UTC.
  Ett tidigt fönster på 12 timmar med inträde 12:00 är tillåtet: signalen är känd vid 12:00. Tecknet som i H-0029
  (inget omvänt tecken).
- Ordning för id: fönster 3, 6, 12 timmar; inom det inträde 12, 18, 21.
- Varianten 6 timmar, 18:00 är identisk med H-0029 och körs igen som kontroll.

## Vad som redovisas

För varje variant: antal affärer, avkastning, avkastning med 2,5 gånger kostnaderna, t, största fall och om de fyra
kriterierna uppfylls med kravet 3,23. Per familj: andelen varianter med positivt t och positiv stressad avkastning.
Alla 50 redovisas, i en fil i research/results/ som aldrig skrivs över. De tre kontrollvarianterna ska återge
H-0027–H-0029 exakt i målpositioner, affärer och resultatsiffror (inte i metadata eller kravet på t); gör de inte det
stoppas analysen och felet redovisas.

**Om flera varianter klarar alla kriterier** väljs den med högst t, och vid lika t den med flest affärer. Bara den
går vidare till en ny hypotes för slutprovet.

**Periodens slut.** Ingen affär får ha sitt utträde på eller efter öppningen av datasetets sista stapel, eftersom
motorn aldrig kör den öppningen. (Samma rättning infördes i H-0027–H-0029 efter Codex granskning; den ändrade inga
mål i de sparade körningarna, kontrollerat stapel för stapel.)
