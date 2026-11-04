# 13F-protokoll: kopiera tio kända investerares största innehav

Skrivet och registrerat 2026-11-04, **innan** några innehav eller aktiekurser hämtats. Ändras inte efter
registreringen. Ett annat urval av investerare eller andra regler blir en ny hypotes.

## Idé

Stora amerikanska förvaltare måste redovisa sina aktieinnehav (formulär 13F) senast 45 dagar efter varje kvartal.
Portföljen följer genomsnittet av tio kända långsiktiga investerares största innehav och flyttar pengarna när någon
av dem lämnar en ny redovisning.

## Investerarna (fast lista)

| Förvaltare | CIK |
|---|---|
| Berkshire Hathaway | 1067983 |
| Baupost Group | 1061768 |
| Pershing Square Capital Management | 1336528 |
| Akre Capital Management | 1112520 |
| Markel Group | 1096343 |
| Himalaya Capital Management | 1709323 |
| Appaloosa | 1656456 |
| Third Point | 1040273 |
| ValueAct Holdings | 1418814 |
| Duquesne Family Office | 1536411 |

En förvaltare ingår från sin första 13F-HR i perioden. Har den inte lämnat någon ny på 200 dagar tas den bort tills
nästa redovisning.

## Regler

| Del | Val |
|---|---|
| Källa | SEC EDGAR, ursprungliga 13F-HR (rättelser 13F-HR/A används inte). Bara aktier (`SH`), inte optioner (`putCall`). |
| Per förvaltare | De 10 största innehaven efter marknadsvärde, viktade efter värde inom de tio |
| Portfölj | Lika vikt per förvaltare som ingår. Samma aktie hos flera förvaltare får summan av vikterna. |
| Tidpunkt | En redovisning gäller från **nästa handelsdags öppning efter inlämningsdagen** (inte kvartalets slut). |
| Ombalansering | Varje gång en förvaltare lämnar en ny redovisning. Mellan dem driver vikterna med priset. |
| Saknat pris | Ett innehav utan kurs (okänd CUSIP eller avnoterad) tas bort och vikten fördelas på förvaltarens övriga. Andelen redovisas. |
| Kurser | Dagliga, justerade för split och utdelning, samma källa för portfölj och jämförelse |
| Kostnader | 10 bp per sida på omsatt belopp (courtage, spread, glidning). Stress 2,5 gånger. |
| Kapital | 100 000 USD (för presentation; avkastningen är densamma oavsett belopp) |
| Period | 2014-01-01 till 2024-12-31. Slutprov 2025-01-01 och framåt läses inte in. |
| Jämförelse | SPY (S&P 500) på samma källa och dagar |

## H-0016: beslutskriterier (spår A, research/tracks.md)

`MORE_RESEARCH` om **alla** gäller, annars `REJECT`:

1. t (Newey-West, dagsavkastning) **över SPY** (portföljens avkastning minus SPY:s) ≥ kravet vid körningen: **2,73** (N = 16)
2. Avkastning med 2,5 gånger kostnaderna > SPY:s avkastning
3. Sharpe > SPY:s Sharpe

Kriterium 1 mäter överavkastningen. En portfölj av amerikanska aktier stiger med marknaden, så t på den egna
avkastningen säger inget om förmåga.

## Datakrav (tillagt 2026-11-04, före körning)

Minst **90 %** av portföljvikten ska i genomsnitt ha ett pris vid ombalanseringarna. Annars markeras körningen
`OGILTIG` (datakvalitet) och inget beslut fattas, eftersom bortfallna innehav ofta är uppköpta eller
avnoterade bolag och testet då blir missvisande. Tillägget gjordes när en namnbaserad koppling CUSIP → ticker gav
62 % täckning, innan några kurser hämtats eller något körts.

## Diagnostik (inga beslut)

Varje förvaltare ensam med samma regler redovisas, så att ni ser vem som drog upp eller ned. Det är tio
jämförelser till och väljs inte som strategi efteråt. En vald enskild förvaltare blir en ny hypotes.

## Kända svagheter, skrivna i förväg

- **Urvalet är gjort i efterhand:** investerarna är kända för att de har lyckats. Det gör testet för optimistiskt.
- 13F visar bara långa amerikanska aktieinnehav: inte blankning, kontanter, obligationer eller utländska aktier.
- 45 dagars fördröjning: innehaven kan vara sålda när vi köper.
- Kurskällan kan sakna avnoterade bolag, vilket också gör testet för optimistiskt.
