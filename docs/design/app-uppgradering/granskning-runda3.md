# Designgranskning, runda 3 (appomfattande kvalitetsrunda)

Granskat: den körande appen (webbygget) på Hem, Resultat, Papper, Marknad, Research Lab och Status i dator (1440×900) och mobil (390×844), ljust och mörkt. Bilder: `runda3/fore-*.jpg` (före) och `runda3/efter-*.jpg` (efter), alla tagna ur den körande appen med Playwright, inga mockups. Inspiration (inte mallar): Linear, Stripe, Revolut.

## Konkreta fynd och åtgärder
| # | Fynd | Åtgärd |
|---|---|---|
| 1 | **Hem var halvtomt och saknade visuellt ankare.** Tre likadana mått och en hel tom halva under dem. | Hem är nu en instrumentpanel: papperportföljen som huvudkort med kurva mot S&P 500, uppdelning av testresultat (klarade inte, kunde inte avgöras, väntar), datastatus med tre rader (papper, investerare, prishistorik) och en lista över senast testade idéer. Fortfarande tre mått och en huvudhandling; inga registerord eller id på startsidan. |
| 2 | **Miljöraden "Papper · inga riktiga pengar" flöt som ett piller utanför innehållskolumnen** (olinjerat, 64 px åt vänster). | En tunn linje högst upp i samma kolumn som innehållet. Texten finns kvar överallt. |
| 3 | **Brus: versaler med bokstavsavstånd överallt och dekorativa piller** ("Bakåt i tiden", "Framåt", "Aktualitet"). | Etiketter i vanlig skrift, pillren borttagna, färg bara för status och handling. |
| 4 | **Marknad: 3 års 4h-staplar ritades som en tät fläck och gammal data märktes bara i liten text.** | Diagrammet öppnar på de senaste tre månaderna med snabbval 1M/3M/1Å/Allt (utöver tidsram och indikatorer). Gammal historik får ett tydligt gult märke i diagramhuvudet ("senaste stapel 2024-12-31, 682 dagar sedan"). Källa, aktualitet och attribution oförändrade. |
| 5 | **Resultat: listan visade avklippta meningar i ord-mitten och id som huvudrad.** | Namnet som huvudrad (klipps vid ordgräns), id som lågmäld etikett, status på egen rad, vald rad markerad med accentfärg. |
| 6 | **Inkonsekvent typografi:** minus som bindestreck på Papper, olika kortformer i olika vyer. | Riktigt minustecken överallt, samma kortform (etikett, stor siffra, status, källrad) på Hem, Papper, Research Lab och Status. |
| 7 | **Mobil: diagramhuvudet staplade fyra märken och en full bredds-knapp för ett enda instrument.** | Kompaktare märken, instrumentvalet krymper till sitt innehåll. |
| 8 | **Tomma, laddande och felaktiga lägen:** Skelett vid laddning av diagram, ikon och en rad text i tomt läge, varningsrutor i samma färgspråk (data inte färsk, fel, datafel); tomma listor har eget läge. | Kvar och kontrollerade i alla vyer (se `granskning-runda3.md` och bilder för Marknad utan data i Tauri-körningen). |

## Dolt aldrig
Datakälla, aktualitet, viktiga varningar och REJECT/OGILTIG syns direkt: banner med huvudbeskedet i Research Lab, "kunde inte avgöras (räknas aldrig som godkända)" på Hem, statuspiller i alla listor.

## Kontroller (webbygget)
- Ingen horisontell overflow vid 390, 700 och 1440 px, ljust och mörkt, på alla åtta vyer (Hem, Resultat, Papper, Marknad, Research Lab ×3 flikar, Status).
- Tab genom varje vy: alla fokuserbara element har synlig fokusmarkering; inga JS-fel.
- Kontrast: nyckelparen (text, status, knapp) uppmätta, alla ≥ 4,5:1 (varningstext i ljust läge justerad).
- Ändrar inga handels-, forsknings- eller säkerhetsregler, ger inga löften om avkastning, ingen mäklarkoppling, inga order.
