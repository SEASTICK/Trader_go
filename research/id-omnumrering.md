# Omnumrering av två hypoteser: H-0025 och H-0026

Beslut: Edwin, 2026-11-14 i chatten med Claude ("New IDs on main", därefter godkänd plan).

## Vad hände

Edwin registrerade två hypoteser 2026-11-03 på sin egen gren, före all kod och alla körningar:

| Nummer på Edwins gren | Registreringscommit | Protokoll | Hypotes |
|---|---|---|---|
| H-0016 | `e65012e` | `research/h0016-protokoll.md` | Riskbegränsat squeeze-utbrott på BTC (spår B) |
| H-0017 | `db7f83b` | `research/h0017-protokoll.md` | Riskstyrd tidsseriemomentum på BTC (spår A, skärpta krav) |

Raderna kom aldrig till `main`. Där gavs H-0016 2026-11-04 till 13F-investerarna och H-0017 2026-11-05 till
Pelosi-kopieringen. Båda är körda. Två olika hypoteser hade alltså samma nummer.

## Beslut

| Gammalt nummer (Edwins gren) | Nytt nummer på main | Registreringsdatum | Protokoll |
|---|---|---|---|
| H-0016 | **H-0025** | 2026-11-03, oförändrat | `research/h0016-protokoll.md`, byte-identiskt |
| H-0017 | **H-0026** | 2026-11-03, oförändrat | `research/h0017-protokoll.md`, byte-identiskt |

- Ordningen följer registreringsordningen. H-0024 var redan tagen på en väntande gren.
- Registerraderna på main är Edwins ursprungliga rader ordagrant, med nytt id, den ursprungliga
  registreringscommiten och en notering om omnumreringen i kolumnen för modell och features.
- **De frysta protokollen ändras inte.** Deras text säger fortfarande H-0016 respektive H-0017. Den här filen avgör
  vilket nummer som gäller på main: där betyder H-0016 och H-0017 13F respektive Pelosi.
- **N behålls som det frystes.** Squeezeprotokollet har N = 16 och momentumprotokollet N = 17 (t-krav
  2,754268270633685, N_sok 1 213). Det var antalet försök när protokollen frystes 2026-11-03. Kravet ändras inte i
  efterhand.
- Gamla registerrader, granskningar, audits och statusfiler på grenarna skrivs inte om. Nytt arbete använder H-0025
  och H-0026, gärna med "tidigare H-0016/H-0017 på Edwins gren" vid första nämnandet.
- Implementationen och granskningen av momentumhypotesen (leverans A–D) finns på grenarna `claude/momentum-*` och
  `codex/momentum-*` och är inte mergad. Den behåller sina gamla filnamn och id:n i historiken.

## Följd för försöksräkningen

Main:s egna H-0016–H-0023 räknade sina t-krav utan dessa två försök, eftersom raderna inte fanns på main. Deras
krav blev därmed något för låga (N två för litet). Detta noteras här och ändrar inga gamla rader eller beslut. Alla
dessa försök blev REJECT eller OGILTIG, så inget beslut hade blivit gynnsammare med rätt N. Från och med nu räknar
`count_attempts` båda raderna, eftersom N är antalet olika id i registret.
