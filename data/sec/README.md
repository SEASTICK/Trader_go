# SEC-härledd data

`cusip_ticker_2013_2025.json`: CUSIP → ticker byggd av `engine/traderlab/data/ftd.py` ur SEC:s offentliga
fails-to-deliver-filer 2017-06 till 2024-12 (413 filer). Används av H-0016 (`research/13f-protokoll.md`).
Täcker 99,5 % av topp-10-vikten i de tio förvaltarnas 13F-redovisningar 2013–2024, även avnoterade och
uppköpta bolag. Bygg om genom att ta bort filen och köra `ftd.load_map`.
