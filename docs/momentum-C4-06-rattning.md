# H-0017 rättning C4-06 – säkra felmeddelanden i funding och risk

Datum 2026-11-04. Underlag: [Codex godkännande av C4 på 4241d0e](momentum-C4-granskning-4241d0e.md), fynd C4-06 [P2].
Edwin har gett klartecken till denna avgränsade rättning med syntetiska data. Rättning för Codex granskning, inte
godkänd. Ingen marknadshistorik, ingen H-0017-körning.

## Fynd

Felmeddelanden i de godkända modulerna `momentum_funding.py` och `momentum_risk.py` formaterade ogiltiga indata med
`repr`. Ett vanligt heltal som 10**5000 kan inte skrivas som text med tolkens standardgräns (4 300 siffror), så själva
felmeddelandet kastade ValueError i stället för FundingError eller RiskError.

## Rättning

Alla 13 `repr`-formateringar (nio i funding, fyra i risk) använder nu ledgerns `_show`, som redan används i ledgern och
marginalmodulen sedan C4-04: den ger `repr` när det går och annars en kort beskrivning av typen. Ingen regel,
beräkning, signatur eller validering har ändrats; bara texten i felmeddelanden. Övriga meddelanden i modulerna
formaterar värden som redan har typkontrollerats (tider, strängar, flyttal) och kan inte nå ett sådant heltal.

## Verifiering

- Nya regressioner: 12 i [test_momentum_funding.py](../engine/tests/test_momentum_funding.py) (event_id, time,
  M_ref_time, M_ref_source, rate, M_ref, stress, price_model, account_key, scenario, processed och fas) och 10 i
  [test_momentum_risk.py](../engine/tests/test_momentum_risk.py) (starttid, startkapital, available, version, day,
  decision_time, T i step, bar_open, mark_close och lock_day). Varje fall ger FundingError eller RiskError med ett
  meddelande som kan formateras. 17 av de 22 fäller modulerna på 4241d0e; övriga numeriska fält går redan via ledgerns
  rättade `_num`.
- Alla tidigare 88 funding- och 101 risktester passerar oförändrade; totalt 211 i de två filerna.
- Riktade felprov: var och en av de 13 rättningarna återställdes till `repr` en i taget. 12 fångas. Den trettonde
  (funding, meddelandet "Okänd källa för M_ref") är ekvivalent: raden nås bara när källan redan är en sträng, och en
  sträng kan alltid skrivas ut. Modulerna återställdes och jämfördes byte för byte.

## Påverkan

Funding (C2) och risk (C3) ändras i felmeddelandetexter, så deras godkännanden behöver omprövas för denna revision.
MOM-C02 är redan återöppnad av Codex för C4-06 och ligger kvar som in_progress tills Codex granskat. Ledger, signal,
marginal, protokoll och register är oförändrade.
