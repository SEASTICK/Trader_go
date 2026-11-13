# H-0023 datapreflight

Genererad ur `research/coverage/h0023-datapreflight.json`. **Ingen basis, avkastning, t-statistik eller beta är beräknad, `simulate` har inte körts och inga arkiv från 2025 eller senare har öppnats.**

* Resultat: **OK**
* Krävda månadsfiler: 1093, verifierade mot sparad checksumma: 1093, problem: 0
* Månader som källan inte har: 0
* Källor med oprövad luckfyllnad: 0
* Dagsfiler använda för luckfyllnad (verifierade mot manifest): 84
* BTCUSDT-gränsdagar (F_k och T_k): 15, problem: 0
* Mynt-cykler kontrollerade: 91, kompletta och möjliga att besluta: 91
* Mynt-cykler som skulle ge OGILTIG om de beslutas (data ofullständig eller oprövad): 0

## Problem i arkiven

Inga.

## BTCUSDT-problem

Inga.

## Oprövad luckfyllnad

Inga.

## Skulle ge OGILTIG om beslutad

Inga.

## Checksummor som kompletterats (filerna är oförändrade)

* `raw/binance/spot/BTCUSDT/1d/BTCUSDT-1d-2021-06.zip`: verifierad mot publicerad checksumma och sparad

## Reproduktion

```bash
cd engine
.venv/bin/python -m traderlab.h0023_preflight --fetch   # hämtar saknade filer 2021-03..2024-09 och kör kontrollen
```
