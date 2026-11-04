# H-0017 C6-01 – tredje granskningstillägget

Datum: 2026-11-04. Granskad HEAD: `313d19e873c91f549e9b2333d5870794507275d4`, gren `codex/momentum-c6-review`. HEAD och gren stämmer med uppdraget. Arbetskopian var ren före granskningen.

Endast rättningen i [beslutsunderlaget](momentum-C6-01-beslutsunderlag.md) har granskats mot de två tidigare felen och [föregående tillägg](momentum-C6-01-granskning-beslut-2.md). Edwins val och det redan bekräftade kontraktet omprövas inte. Diffen från `c84a77fa6db635ff95da1aaa025228dc2c855028` i underlaget ändrar enbart fall 5.

**Fel 1 är åtgärdat.** Oberoende omräkning med Python `decimal.Decimal`, precision 60, verifierar samtliga 18 ordnade punkter i fall 5: löpande peak, varje drawdown och ackumulerat minimum. De återkommande decimalerna är korrekt avrundade till tio decimaler i tabellen. Peak höjs från 100 000 till 110 000 i stapel 1 och behålls. Lokala minima är exakt −0,4, −0,25 och −1. Efter stapel 2 kvarstår tidigare minimum −0,4; stapel 3 ger först −8/11 vid low och sedan −1 vid likvidationsnollan. Det är ett syntetiskt punktprov av boundberäkningen, inte ett separat verifierat marginal-/motorförlopp.

Fall 4 har också räknats om: funding ±4 000, C_high −296 000, C_low −304 000, E_high 144 000, E_low −24 000, MM_open 20 000 och MM_low 14 000. High höjer peak och low ger −7/6; nollpunkten ändrar inte minimum. Med peak 100 000 hade low gett −1,24. Facit och reservation stämmer.

**Fel 2 förblir åtgärdat.** Konsekvensavsnittets avgränsning till ekonomisk klassificering REJECT/MORE_RESEARCH för giltig main-körning, åtskillnaden från OGILTIG/OGILTIG_DATA samt lokalt kontra ackumulerat minimum är kvar. Open använder ingående C/q och high/low använder q_open. Inga nya sakfel har identifierats i rättningen.

**Bedömning: KLART FÖR IMPLEMENTATION av C6-01 enligt det redan bekräftade kontraktet.** Detta godkänner ingen implementation eller full C6/MOM-C04-leverans. Endast denna nya fil har skapats enligt uppdraget; statuskällor och checklistor har inte ändrats eller regenererats. Ingen commit, motorkörning, historikkörning eller drift. H-0013 förblir REJECT; H-0016 berörs inte.
