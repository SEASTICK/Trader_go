# Punkt-i-tid-underlag: Binance COIN-M-kvartalskontrakt (ADA, BCH, BNB, DOT, LINK, LTC, XRP)

Datum: 2026-11-12. Uppdrag från Codex efter PR #114. **Ingen hypotes registreras och inget backtest körs här.** H-0022 är
fortfarande oregistrerad (N = 21). Meddelanden och data från 2025-01-01 och senare är inte använda; inget pris, ingen
avkastning och ingen basis har räknats eller använts för urval.

## Vad som levereras

| Fil | Innehåll |
|---|---|
| `coinm-pit-series.json` / `.csv` | En rad per (underliggande, förfall): daterad annons, observerade staplar, status, kontraktsstorlek med status |
| `coinm-pit-events.json` | De 24 tolkade listningsmeddelandena före 2025: datum, kod, vilka underliggande, vilka serier, vilka som uttryckligen *inte* listades |
| `research/coverage/basis-sources-ann1-*.json`, `…pit1-*.json` | Rådata: de 1 378 titlar i Binance-katalogerna 48, 49 och 161 som matchade ett ordfilter (COIN-M, quarterly, delivery, delist m.fl.) och hela texten i 24 listningsmeddelanden |
| `engine/traderlab/pit_universe.py`, `pit_observed.py` | Koden som bygger tabellen (`python -m traderlab.pit_universe`), med tester i `engine/tests/test_pit_universe.py` |

`universe_at(rader, dag)` är **fail-closed**. En serie är valbar en beslutsdag först när den både var offentligt meddelad och
faktiskt handlades: daterad annons ≤ dagen, förfall > dagen, granskad data finns, serien är inte uttryckligen `not_listed`
och **en verifierad stapel med volym > 0 finns just den dagen** (`traded_runs`). Intervallet mellan första och sista handlade
stapel räcker inte: en dag som saknas eller har nollvolym innanför intervallet är aldrig valbar, och `universe_report` redovisar
den under `active_without_verified_bar` med orsak (`data_gap`, `data_gap_unverified`, `zero_volume`). Annonserade men ännu ohandlade serier (119 av de 135
har första handel efter annonsen), serier utan hämtad data och serier utan daterad annons returneras aldrig.
`universe_report(rader, dag)` visar dessutom vad som hölls utanför och om urvalet är ett efterhandsurval den dagen.
Exempel (de sju, bara valbara serier): 2020-07-25 → 0 (ADA/LINK 0925 är annonserade men datan börjar först 2020-08-01, så de
utesluts konservativt); 2020-08-15 → 2 (ADA, LINK); 2020-11-10 → 8; 2020-12-01 → 12 (BCH 1225/0326 är annonserade 2020-11-30
men första handel är 2020-12-03, så de är inte med förrän då); 2020-12-03 → 14; 2021-03-26 → 7; 2024-12-01 → 14.

## Daterade källor (primärkälla: Binance-meddelanden)

| Underliggande | Första offentliga listningsmeddelande | Kanal |
|---|---|---|
| ADA | 2020-07-20 (0925) | Binance Futures Will Launch ADAUSD Quarterly 0925 |
| LINK | 2020-07-21 (0925) | motsvarande |
| BNB, DOT | 2020-11-03 (1225 och 0326) | Launch BNBUSD and DOTUSD Quarterly 1225 & 0326 |
| XRP, LTC, BCH | 2020-11-30 (1225 och 0326) | Launch XRP, LTC, EOS, BCH Quarterly 1225 & 0326 |

Därefter listas varje ny serie via ett gemensamt meddelande 0–7 dagar före föregående leverans (2020-12-25 till 2023-06-27:
tio meddelanden "Coin-Margined Quarterly"; 2023-09-25 till 2024-12-20: sex meddelanden "USDⓈ-M & COIN-M Quarterly"). Varje meddelande namnger vilka
underliggande som listas. Mellan meddelandet och första handlade stapel gick 0–12 dagar (oftast 2–7), eftersom
listningen sker efter att den föregående serien löpt ut.

## Resultat

* **135 serier** för de sju (förfall 2020-09-25 till 2025-06-27), varav **128** har både daterad annons och observerade
  staplar före 2025.
* **7 serier (förfall 2021-09-24, en per underliggande) saknar daterad annons** i katalogerna 48, 49 och 161, trots att
  data visar att de handlades. Serien före (0625) annonserades 2020-12-25 och serien efter (1231) 2021-06-23, så annonsen
  för 0924 borde ha kommit i mars 2021 men finns inte bland de 1 378 titlarna. De är därför **osäkra**: de kan
  användas i ett test bara om en daterad annons hittas, annars måste testet stoppa eller utesluta serien.
* **Ordinarie sista handelsdag:** alla 135 förfall är sista fredagen i mars, juni, september eller december, i linje
  med leverans-FAQ:n (08:00 UTC). Ingen serie slutar handlas före förfall i data (`ended_before_expiry` = 0).
* **Staplar efter förfall:** arkivet fortsätter kurvan med nollvolym efter förfall (6, 11 eller 18 dagar för 21 serier,
  109 dagar för ADA/LINK 0925). **Sista stapel är därför inte sista handelsdag**; tabellen anger `last_traded_bar`
  (sista stapel med volym) separat.
* **Censurering:** ADA/LINK 0925 börjar före vår datastart 2020-08-01 (vänstercensurerade). 14 serier (förfall
  2025-03-28 och 2025-06-27) slutar i data 2024-12-31 och är högercensurerade (verkligt förfall senare).
* **Luckor:** 14 serier (0929 och 1229 2023, sju vardera) saknar 2023-08-28..31 i månadsfilerna. Dagarna är fyllda med
  **verifierade** dagsstaplar ur dagsarkivet (#113: checksumma, SHA-256 mot manifestet, grannkontroll, `gapcheck.combined`) och
  markerade per serie i `daily_filled_days` (4 dagar vardera). Går verifieringen inte igenom lämnas luckan öppen
  (`gap_fill_unverified`, `missing_days`) och dagen är inte valbar. Nollvolym- och saknade dagar innanför intervallet: 0 serier
  efter fyllnaden. Nollvolymstaplar före första handel och efter förfall räknas aldrig som observerad handel.
* **Avnoteringar:** i katalog 161 före 2025 finns inga avnoteringsmeddelanden för kvartalskontrakten i de sju. De
  COIN-M-avnoteringar som finns gäller terminer utan förfall (LUNA, CRV, GALA, ZIL, VET, KNC, ICX, XTZ, ROSE, APE). Det
  gäller titlar i tre kataloger och är inte ett bevis för att inget annat hände.

## Överlevnadsbias: de sju är ett efterhandsurval före 2021-03-26

EOS, ETC, FIL och TRX fick 1225- och 0326-serier (annonser 2020-11-30 och 2020-12-07) men **listades uttryckligen inte**
för 0625: meddelandet 2020-12-25 anger "ETC, TRX, EOS and FIL quarterly 0625 contracts will not be listed". De hade
alltså aktiva serier fram till sista förfallet **2021-03-26**. Så länge de var aktiva är de sju ensamma ett efterhandsurval
(valt bland dem som fortsatte), inte ett punkt-i-tid-universum. Den tidigare gränsen 2020-12-25 i en tidigare version av
rapporten var för tidig och är rättad. De fyra ligger i tabellen (`in_target_seven` = falskt, `data_checked` = falskt, ingen
data hämtad) och `universe_report` flaggar `hindsight_selection` = sant för varje dag då en av dem hade en aktiv serie.

Ytterligare ett urval gäller i andra änden: SOLUSD COIN-M-kvartal lanserades 2024-08-14 (meddelande 2024-08-08) och ingår inte
i de sju. BTC och ETH är uteslutna i förväg (de är inte nya underliggande), inte på grund av överlevnad.

**Biasfritt fönster för de sju: beslutsdag från och med 2021-03-26 till och med 2024-08-13** (`hindsight_free_window` i
koden). Utanför det fönstret krävs antingen ett komplett universum (de fyra hämtade och inkluderade före 2021-03-26, SOL
inkluderad från 2024-08-14) eller att testet stoppas. I fönstret listar alla funna meddelanden (2020-12-25 till 2024-06-19) exakt BTC, ETH och de sju, så ingen annan altcoin-kandidat
är bortvald i dem. Meddelandet för 0924-serien (2021) saknas, så för den serien går det inte att kontrollera.

## Kontraktsstorlek: antagande, inte fakta

Inget av de 24 listningsmeddelandena anger kontraktsstorlek. Det som är belagt är den generella regeln (altcoin-kontrakt
10 USD i Binance-guiden 2020-06-12, ETH = 10 USD i förklaringen 2021-07-26; se `research/h0022-forutsattningar.md`).
Tabellen anger därför `contract_size_usd` = 10 och `contract_size_status` = `assumed_general_rule` för alla rader.
Det är ett **uttryckligt antagande**, inte verifierat för respektive kontrakt och period.

## Vad som kan väljas, vad som är osäkert, vad som måste stoppa ett test

| Kategori | Serier | Följd för ett framtida test |
|---|---|---|
| Kan väljas vid beslutsdagen | 128 serier med daterad annons och staplar, från och med sin första handlade stapel | Ja, om universumet byggs med `universe_at` och beslutsdagen ligger i det biasfria fönstret 2021-03-26 till 2024-08-13 |
| Osäkra | 7 serier (förfall 2021-09-24) utan daterad annons; alla 135 på grund av antagen kontraktsstorlek; 14 serier där augustiluckan är fylld ur dagsarkivet (proveniens markerad); ADA/LINK 0925 vänstercensurerade; 14 högercensurerade serier | Kräver extra belägg eller uttryckligt undantag |
| Måste stoppa testet (fail-closed) | Beslutsdag före 2021-03-26 om EOS/ETC/FIL/TRX utelämnas, eller från 2024-08-14 om SOL utelämnas; en serie som är annonserad men ännu inte handlad; en serie utan daterad annons; en serie vars kontraktsstorlek ändrats; en lucka i markpris eller kurs som inte kan lagas | OGILTIG, inte MORE_RESEARCH |

## Kvarvarande luckor (avgränsade)

1. Daterad annons för 0924-serien (2021). Kan finnas i en katalog som inte listats; sök på titel i en separat körning.
2. Kontraktsspecifik, daterad storlek per underliggande. Utvecklarsidan renderades med 0 tecken; live-API:t svarar 451.
3. Marginaltabeller: meddelandena 2020-12-22 (FIL, ETC, TRX, EOS) och 2023-05-31 (flera COIN-M) innehåller tabeller för vissa
   kontrakt. De är en möjlig källa för blockerare 3 i `h0022-forutsattningar.md` men ingår inte här.
4. Avräkningsfönstret (timmesmedel i guiden 2020 mot 30 minuter i nuvarande FAQ) är fortfarande oklart.
5. EOS/ETC/FIL/TRX-data (krävs för beslutsdagar före 2021-03-26) och SOL-data (krävs från 2024-08-14).

## Status

Ingen hypotesregistrering, inget backtest, inga order. `research/registry.md` är oförändrad. Rapporten gäller de sju; den är inte
ett komplett COIN-M-universum.
