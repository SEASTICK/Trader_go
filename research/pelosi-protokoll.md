# Pelosi-protokoll: kopiera Nancy Pelosis redovisade aktieaffärer

Skrivet och registrerat 2026-11-05, **innan** några redovisningar eller kurser för Pelosi hämtats. Ändras inte
efter registreringen.

## Idé

Ledamöter i USA:s representanthus måste redovisa aktieaffärer (Periodic Transaction Report, PTR) senast 45 dagar
efter affären. Nancy Pelosis redovisningar (affärerna görs till största delen av maken Paul Pelosi) är kända för
god avkastning. Portföljen köper det hon redovisar att hon köpt, säljer det hon redovisar att hon sålt, och gör
det först **dagen efter att redovisningen blivit offentlig**.

## Regler

| Del | Val |
|---|---|
| Källa | House Clerk: årsindex `YYYYFD.zip`, rader med efternamn Pelosi, förnamn Nancy och typ P (PTR). Redovisningen läses från `ptr-pdfs/<år>/<DocID>.pdf`. |
| Affärer | Tillgångstyp aktie (`[ST]`) och optioner (`[OP]`). Köp (`P`) av aktie eller köpoption räknas som köp av aktien. Försäljning (`S`) av aktie räknas som sälj; delförsäljning (`S (partial)`) ändrar inget. Säljoptioner, obligationer, fonder och övrigt räknas inte. |
| Innehav | Aktier med ett redovisat köp de senaste 365 dagarna, utan en senare redovisad hel försäljning |
| Vikter | Lika vikt per aktie (beloppen redovisas bara som intervall) |
| Tom portfölj | Hela kapitalet i SPY |
| Tidpunkt | Ombalansering vid öppningen första handelsdagen efter redovisningens inlämningsdag |
| Kostnader | 10 bp per sida på omsatt belopp, stress 2,5 gånger |
| Kurser | Dagliga från Stooq, justerade för split och utdelning, samma källa som SPY |
| Period | Redovisningar inlämnade 2014-01-01 till 2024-12-31. Slutprov 2025-01-01 och framåt läses inte in. |
| Datakrav | Minst 90 % av de redovisade köpen ska gå att tolka till en ticker med kurs, annars `OGILTIG` utan beslut |

## Förtydligande om tolkningen (2026-11-05, före körning)

Redovisningar från 2014–2015 saknar typtaggarna `[ST]`/`[OP]` och skriver optioner bara som "Purchase of N Options".
De tolkas så här, bestämt efter att ha sett texten men innan något resultat räknats:

- En rad utan tagg är en aktie, om inte beskrivningen nämner optioner.
- Ett optionsköp utan angiven typ räknas som köpoption, om ordet "put" inte förekommer.
- Inskannade redovisningar utan text räknas som otolkade och ingår i datakravet.
- Redovisningar som bara gäller fastigheter (ingen ticker alls) har inga aktieaffärer och räknas varken som
  tolkade eller otolkade.

## H-0017: beslutskriterier (spår A)

`MORE_RESEARCH` om **alla** gäller, annars `REJECT`:

1. t (Newey-West, dagsavkastning) för avkastningen **över SPY** ≥ kravet vid körningen: **2,75** (N = 17)
2. Avkastning med 2,5 gånger kostnaderna > SPY:s avkastning
3. Sharpe > SPY:s Sharpe

## Kända svagheter, skrivna i förväg

- **Urvalet är gjort i efterhand och i hög grad:** Pelosi väljs just för att hennes affärer är kända för att ha gått
  bra. Det gör testet kraftigt för optimistiskt, och ett godkänt resultat ska ses med stor försiktighet.
- Få affärer: troligen några tiotal aktier under tio år, så testet har låg styrka.
- Beloppen är intervall, så lika vikt är en förenkling. Optioner (ofta djupa köpoptioner) räknas som aktier.
- Redovisningarna kommer upp till 45 dagar efter affären, ibland senare.
- PDF-tolkningen kan missa affärer. Andelen redovisas.
