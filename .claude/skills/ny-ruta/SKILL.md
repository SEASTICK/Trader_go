---
name: ny-ruta
description: Använd när en ny ruta (ett experiment, till exempel "BTC 4h") ska läggas till i Research, när en ruta ska få riktiga siffror, eller när någon vill ta bort eller sålla rutor efter resultat.
---

# Ny ruta i Research

En ruta är ett test av **en idé på en marknad och en tidsram**. Rutorna ligger i `app/data/experiments.json` och visas av `app/src/pages/Research.tsx`.

## Lägga till en ruta

Lägg en rad i `experiments.json`:

```json
{ "id": "E-17", "spår": "S-01", "namn": "SOL 4h", "strategi": "Krypto trend/momentum", "grupp": "krypto", "marknad": "Solana", "tidsram": "4h", "riktning": "Long/short" }
```

- `id`: nästa lediga `E-NN`. Återanvänd aldrig ett id.
- `spår`: ett id från `app/data/tracks.json`.
- `grupp`: en av `krypto`, `terminer`, `aktier`, `makro`, `baslinje`. Kategori efter marknad.
- `tidsram`: `1h`, `4h`, `1d` eller `1 mån`.

Kör `npm --prefix app test` och `npm --prefix app run build`. En ruta visas i Research först när den har ett riktigt
resultat i `app/data/results.json`. Appen visar aldrig påhittade siffror. Lägg därför till rutan när hypotesen är
registrerad, inte som en lös idé (idéer hör hemma i `docs/vagen-till-avkastning.md`).

## Från idé till ruta

En ruta syns först efter, i ordning:

1. **Data** hämtad och kontrollerad (`hamta-data`).
2. **Hypotesen registrerad och committad** i `research/registry.md` innan något körs (`ny-hypotes`).
3. **Backtest** med kostnader, gallring och reglerna i `CLAUDE.md`.
4. **Granskning** (`granska-backtest`) och beslut: `REJECT`, `MORE_RESEARCH` eller `READY_FOR_PAPER`.

Sedan exporteras resultatet (`traderlab.batch.export_to_app`) och rutan syns med riktiga siffror.

## Sålla bland rutor

- **Ta aldrig bort en ruta för att den gick dåligt.** Den sätts till `REJECT` och räknas fortfarande som försök.
- Kravet på t-värde räknas på **alla** rutor (Bonferroni, minst 2,0): 17 rutor ger cirka 2,8, 100 rutor cirka 3,3. Fler rutor ger strängare krav.
- Att behålla de bästa av många ger falska vinnare. Bara rutor **över kravet** och som håller på **ny data** går vidare till papper (`papper-framat`).
- Säg det rakt ut när någon vill sålla på avkastning ensam.
