# H-0017 C6-01 – tillägg till granskningen

Datum: 2026-11-04. Granskad HEAD: `c84a77fa6db635ff95da1aaa025228dc2c855028`, gren `codex/momentum-c6-review`. HEAD och gren stämmer med uppdraget; arbetskopian var ren före granskningen.

Endast rättningen i [beslutsunderlaget](momentum-C6-01-beslutsunderlag.md) har prövats mot de två felen i [föregående granskning](momentum-C6-01-granskning-beslut.md). Edwins val och det bekräftade kontraktet omprövas inte.

**Fel 1 är delvis åtgärdat.** Oberoende omräkning med Python `decimal.Decimal`, precision 60, bekräftar fall 4: p = ±4 000, C_high = −296 000, C_low = −304 000, MM_open = 20 000 och MM_low = 14 000. Punktsekvensen är 100 000, 100 000, 100 000, 144 000, −24 000, 0. High höjer peak till 144 000; low ger exakt −7/6 och blir både lokalt och ackumulerat minimum. Nollan ger −1 och ändrar inte minimum. Med oförändrad peak 100 000 blir low i stället −1,24. Tabell och reservation stämmer.

**Kvarstående brist:** fall 5 (underlagets rader 141–143) anger bara färdiga minima, inga ordnade kapitalpunkter eller peakvärden som de kan räknas fram ur. Decimal bekräftar min(−0,40; −0,25) = −0,40 och min(−0,40; −1) = −1, men det verifierar endast jämförelsen, inte de påstådda lokala minima eller förloppet utan träff. Föregående granskning krävde uttryckligen syntetiska ordnade punkter med oberoende facit för även detta förhållande. Komplettera fall 5 med kapitalpunkter och löpande peak, lokal drawdown och ackumulerat minimum som visar att tidigare minimum styr. Inget nytt Edwinval behövs.

**Fel 2 är åtgärdat.** Konsekvensavsnittet avgränsar slutsatsen till ekonomisk klassificering REJECT/MORE_RESEARCH för giltig main-körning med oförändrade övriga serier, skiljer OGILTIG/OGILTIG_DATA och lokalt från ackumulerat minimum. Open använder ingående C/q före A-funding och fill; high/low använder q_open. Inget nytt sakfel har identifierats i dessa rättningar eller fall 4.

Bedömning: **BEHÖVER RÄTTAS**, enbart den kvarstående exemplifieringen i fel 1. Detta godkänner ingen implementation eller full C6-leverans. Endast denna fil har skapats; status, checklistor och övriga filer lämnas orörda enligt uppdraget. Ingen commit, motorkörning, historikkörning eller drift. H-0013 förblir REJECT; H-0016 berörs inte.
