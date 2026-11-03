# H-0017 leverans C2 – fundingbokföring mom-funding/1.0.0

Datum 2026-11-03. Rättad efter [Codex granskning av 1d9359f](momentum-C2-granskning-1d9359f.md): fasen kontrolleras
mot eventets exakta tid (C2-01), behandlade event-id valideras före normalisering (C2-02) och en källa som inte är
sträng ger FundingError. Ledgern är oförändrad sedan 1d9359f. Underlag: [research/h0017-protokoll.md](../research/h0017-protokoll.md) §8.1, §8.3, §12, §15, D03,
D18, D19 och [uppdraget](claude-uppdrag-momentum-C2.md). Implementation för Codex granskning, inte godkänd. Endast
syntetiska konton och event; ingen marknadshistorik har lästs och ingen H-0017-körning har startats. B-modulen,
protokollet och registret är orörda.

## API

Modul: [engine/traderlab/momentum_funding.py](../engine/traderlab/momentum_funding.py), `VERSION = "mom-funding/1.0.0"`.

| Del | Beskrivning |
|---|---|
| `FundingEvent(event_id, time, rate, M_ref, M_ref_source, M_ref_time)` | exakt UTC-tid med högst millisekundupplösning, ändlig ränta, M_ref > 0, källa och tid för priset |
| `bar_open(t)` | öppning för 4H-stapeln som innehåller t; vid exakt gräns stapeln som börjar där |
| `FundingConfig(stress=False, price_model="mark_open")` | märkt konfiguration; `label` är `mark_open`, `mark_open+stress`, `mark_close` eller `mark_close+stress` |
| `FundingState(account_key, scenario, processed)` | redan bokförda event-id för ett konto i ett scenario; `processed` måste vara set, frozenset, list eller tuple av hela, icke-tomma strängar (även vid `dataclasses.replace`) |
| `apply_funding(acct, state, event, phase, config)` | bokför en händelse på det givna kontot; returnerar nytt konto, nytt tillstånd och `FundingRecord` |
| `FundingRecord` | event_id, exakt tid, fas, konto, scenario, konfiguration, q vid avräkning, ränta, M_ref med källa och tid, payment_base, payment, C och E före och efter, version |
| `FundingError` | underklass till `LedgerError`; ogiltigt event, konfiguration, fas eller dubbelbokning |

Faser: `funding_A` (samtidig händelse på q före affären), `funding_B` (samtidig händelse på q efter affären) och
`funding_interior` (mellanhändelse på q vid t). Fasen måste passa eventets exakta tid: `funding_A` och `funding_B`
bara när tiden är exakt en 4H-gräns, `funding_interior` bara strikt mellan två gränser (även ±1 ms från gränsen är en
mellanhändelse). Ingen tolerans eller avrundning. Funktionen avgör inte vilken position som gäller; det gör kommande
eventlager, som också gör marginalkontrollen före fyllning.

## Regler

- Betalning = q × M_ref × ränta. Positivt belopp betalas och minskar C, negativt tas emot och ökar C. Long,
  legacy-short och platt konto behandlas lika.
- M_ref följer D03: `M_ref_time` måste vara öppningen för stapeln som innehåller eventtiden (`mark_open`). Diagnostiken
  `mark_close` (stapelns slut) kräver uttrycklig konfiguration; ett event vars källa inte matchar konfigurationen avvisas.
- Tiden används exakt. Ingen tolerans, avrundning till 4H-gräns eller fördelning över stapeln.
- Fundingstress dubblar bara positiva betalningar; tecknet på den faktiska betalningen avgör, inte räntans tecken.
- Ett event bokförs högst en gång per (konto, scenario). Även ett nollbelopp på platt konto räknas som behandlat.
  En ensam sträng eller bytes som `processed` avvisas i stället för att tolkas som en mängd tecken, så ett återställt
  id kan inte tappas och leda till dubbelbokning.
  Samma event-id kan bokföras i andra kontons eller scenariers egna tillstånd.

## Ledgerkomplettering (C01 återöppnad)

`Account` i [momentum_ledger.py](../engine/traderlab/momentum_ledger.py) har fått fältet `funding_net` (netto betald
funding, standard 0, samma ändlighetskontroll som övriga fält). Funding hålls skild från `realized` och `costs`.
Avstämning: C = C0 + realized − costs − funding_net − q × avg_price. När funding_net = 0 är det C1:s identitet; gamla
konstruktioner och fyllningar fungerar oförändrat och alla 82 C1-tester passerar utan ändring.

## Fel

FundingError eller LedgerError utan ändrat konto eller tillstånd: naiv eller icke-UTC tid, tid som inte är en
pd.Timestamp, finare upplösning än millisekund, icke-ändlig eller bool ränta, M_ref ≤ 0 eller icke-ändligt, tomt eller
icke-strängt event-id, källa som inte är sträng, okänd källa, M_ref_time som inte följer prismodellen, källa som inte matchar konfigurationen,
okänd fas, fas som inte passar eventets tid, ogiltig `processed`-samling eller ogiltigt id-element, dubbelbokning och overflow i belopp eller kapital från ändliga argument. Numpy- och Python-tal ger samma
bokföring.

## Verifiering

- [engine/tests/test_momentum_funding.py](../engine/tests/test_momentum_funding.py): 88 tester, alla godkända. De 41
  nya regressionerna för granskningen: alla tre faser mot exakt gräns, ±1 ms och ±30 s; sträng, bytes, None, tal,
  dict och iterator som `processed`; tal, bool, None, tom sträng, bytes och float som id-element; giltiga samlingar som
  bevarar hela id; återställt `f1` som avvisar andra bokningen utan kontoändring medan ett separat scenario fungerar;
  fem icke-strängkällor. 27 av dem fäller den granskade revisionen 1d9359f. Två befintliga tester som matade fel fas
  (millisekundtestet med funding_A för en mellanhändelse och sekvenstestet med funding_interior på 4H-gränser) har
  fått rätt tid och fas med oförändrat ekonomiskt facit. Facit från
  [orakelfilen](momentum-a1-orakel.json) och Decimal-räkning:
  - O5 inträde och utgång i A och B, komponerat av C1-fyllningar och fundingfunktionen i låst ordning; O5b med
    E_trade och E_post som skilda faser och funding varken som kostnad eller realiserat.
  - O16: exakt gräns och ±30 sekunder med bevarade tider, rätt UTC-dag och rätt stapel för M_ref.
  - O17: konto stängt vid öppningen betalar 0; nytt inträde använder den nya positionen q_open (9,98403).
  - Long, short och platt med positiv, negativ och noll ränta; flera event; dubbelbokning; samma event i tre separata
    konton/scenarier; nollbelopp som inte kan debiteras efter ny position; stress för alla fyra teckenkombinationer.
  - Funding följt av partialaffär, vändning, hold och full stängning, där C stäms av mot Decimal efter varje steg och
    avstämningsidentiteten håller.
  - 14 ogiltiga event, millisekundtid, overflow och fel fas utan ändring, numpy mot Python, spårpostens fält,
    validering av funding_net och avstämning med funding_net.
- Tillsammans med ledgertesterna: 170 godkända.
- Riktade felprov efter rättningen: de 15 tidigare och 5 nya (A/B tillåten mellan gränser, interior tillåten på
  gräns, `processed` normaliserad tyst, id-element ovaliderade, källa utan typkontroll). Alla 20 fångas.
- Riktade felprov i första leveransen: 15 avsiktliga fel infördes ett i taget i fundingmodulen eller ledgern. Alla 15 fångades: fel tecken,
  tillåten dubbelbokning, abs(q) i stället för q, stress som dubblar krediter, stress efter räntans tecken, stress
  ignorerad, funding bokförd som kostnad, nollbelopp inte markerat som behandlat, M_ref_time ej kontrollerad,
  mark_close tillåten i huvudmodellen, fas ej kontrollerad, sub-ms-tid tillåten, icke-UTC-tid tillåten, funding_net
  saknas i avstämningen och funding_net ovaliderat. C1:s ledgerfel kördes om mot den kompletterade ledgern med samma
  utfall som i C1 (19 fångade, en ekvivalent). Modulerna återställdes och jämfördes byte för byte.

## Utanför C2

Ingen marginal eller likvidation, dagsreset, band- eller signalbeslut, dags- eller permanent stopp, intrastapel-bound,
full event- eller riskloop och ingen L1/L2-orkestrering. Hela MOM-C03 kräver också dagsreset och första/sista event.
Endast syntetiskt prövat.
