# Teknisk reproduktion av Fas 1, 2026-11-02

Registreras före strategikörningen. Detta är en teknisk audit av H-0009–H-0012,
inte nya hypoteser eller ett nytt oberoende bekräftelsetest. Alla fyra tidigare
REJECT-beslut behålls. Inga strategier godkänns för papper genom denna audit.

- Oförändrade strategier, sökrymder, seed 0, 40 försök per optimering och sex
  växande walk-forward-fönster enligt research/fas1-protokoll.md.
- Endast Binance BTCUSDT USDⓈ-M 4H från 2020-01-01 till exklusivt 2025-01-01,
  med faktisk funding. Filer från slutprovet får inte öppnas.
- Ingen historik före 2020 krävs i den registrerade motorn: indikatorerna börjar
  värmas från utvecklingsperiodens början. Första OOS-fönstret börjar 2022.
- Varje originalfil verifieras mot Binance SHA256. Datasetet identifieras av
  ett fryst manifest och hashes av de normaliserade tabellerna. Ingen imputation,
  tidsförskjutning, borttagning av utstickare eller spot/futures-substitution.
- Kontrollera alla kvalitetsflaggor. Jämför tolv utstickare med Coinbase BTC-USD
  spot; olika instrument innebär att priserna inte måste sammanfalla. Skillnader
  över två procentenheter flaggas och behålls synliga. Ingen datarensning görs.
- Kör strategier sekventiellt utanför den aktiva kön. Bevara varje Optuna-försök,
  även PRUNED/FAIL, och spara fel och avbrutna auditkörningar.
- Redovisa samma fyra ursprungliga beslutskriterier med tolv ursprungliga
  hypotesförsök samt alla 1120 parameterförsök separat. Kriterierna ändras inte.
- Redovisa kostnadsstress 2.5x, buy-and-hold, block-bootstrap Sharpeintervall,
  årsresultat, resultat utan bästa året och tidsstämplade data-/kodversioner.
- Upprepa OOS-utvärderingen med samma valda parametrar och kontrollera identisk
  kurva. Ingen ny parameteranpassning efter resultatet. Slutprovet hålls låst.

Begränsningar: utvecklingsperioden har redan använts för forskning; ett nytt
fildataset gör den inte orörd. Kontrakts-OHLC används, separat mark-price och
likvidationsprecision är inte verifierade här. Auditens kriterier kan inte
upphäva tidigare REJECT eller ersätta Fas 1:s slutliga godkännande.
