# H-0022 (COIN-M kassa-och-termin): förutsättningar kontrollerade, EJ förregistrerad

Datum: 2026-11-12. Uppdraget var att förregistrera en enda ny basis-hypotes före motorkod och före någon historisk körning,
men att **inte** registrera en skenbart körbar hypotes om kontraktstorlek, markpriser eller avräkning inte går att verifiera
tillräckligt. Den här filen redovisar vad som kontrollerats mot primärkällor och vad som saknas.
**Beslut: ingen rad läggs i `research/registry.md`. N förblir 21.** Ingen avkastning, ingen basis och ingen hållperiod har
räknats, och data från 2025 och senare är inte läst.

Underlag: `research/coverage/basis-sources-runner6-20261112T153533Z.json` (hel artikeltext hämtad från en GitHub-runner,
eftersom binance.com inte nås från utvecklingsmiljön), samt tidigare `research/basis-uppfoljning-data.md` och
`research/cm-lucka-2023-08.md`.

## Vad som är verifierat mot primärkälla

| Förutsättning | Källa | Gäller 2020–2024? |
|---|---|---|
| BTCUSD-kontrakt = 100 USD, PnL i mynt = n · storlek · (1/inträde − 1/utträde) | Binance FAQ om PnL (artikel 3a55a237…) | Sidan är en nutida version; ingen historik för storleken är kontrollerad |
| Kvartalskontrakt förfaller sista fredagen i mars/juni/sep/dec kl 08:00 UTC | Binance FAQ om leverans (a3401595…), exemplet BTCUSD 0925 = 2020-09-25 | Ja, exemplet är från 2020 |
| Avräkningskurs = medel av indexpriset varje sekund 07:30–08:00 UTC (1 800 värden) | samma | Sidan är nutida; ingen datumangiven historik |
| Avräkningsavgift = takeravgiften; avräkning kan skjutas upp vid manipulation | samma | som ovan |
| Orealiserad PnL räknas på Mark Price, och avgiften dras ur realiserad PnL | FAQ om PnL och leverans | som ovan |
| COIN-M-avgift för vanlig användare ändrades 2023-09-26 04:00 UTC: maker 0,010 % → 0,020 %, taker 0,050 % → 0,050 % | Binance-meddelande 2023-09-18 (f4433fc2…) | Ja, datumsatt. Visar bara nivån *strax före* ändringen, inte när den började gälla |
| Dagsstaplar för markpris per terminskontrakt och indexpris per par finns i arkivet till och med 2024-12 | S3-listning av data.binance.vision (se PR #113 och dessa körningar) | Ja, men ej kontrollerat kontrakt för kontrakt |
| Luckan 2023-08-28..31 går att täcka med verifierad dagsdata | `research/cm-lucka-2023-08.md` | Ja |

## Vad som INTE är verifierat och därför blockerar en ärlig förregistrering

1. **Kontraktstorlek för andra underliggande än BTC.** Antagandet 10 USD (ETH, ADA, BCH, BNB, DOT, LINK, LTC, XRP) saknar
   primärkälla. Utvecklarsidan för Exchange Information levererade 0 tecken (sidan byggs med JavaScript), och live-API:t
   svarar 451 från vår miljö (och ska inte kringgås). Utan storlek går inte heltalsavrundningen eller restexponeringen att
   låsa. Det räcker för att stoppa ett test på "delvis nya underliggande".
2. **COIN-M-avgifter före 2023-09-26 och spotavgifter över tid.** Endast nivån strax före ändringen är känd; startdatum,
   VIP-nivåer och BNB-rabatt är okända. Spotavgifter 2020–2024 är inte hämtade alls.
3. **Maintenance Margin-tabellerna (marginalnivåer per notional) per kontrakt och period.** FAQ:n ger formeln och *ett*
   BTC-exempel (300 BTC → 12,5 %, avdrag 11,605 BTC), men hänvisar till sidan "Leverage & Margin", som inte hämtats. Utan
   den går en likvidationsmodell baserad på markpris inte att låsa för varje underliggande.
4. **Regler för tidig avnotering eller ändrad avräkning** (t.ex. kontrakt som stängts före förfall) saknas. Arkivet visar
   att flera produktlinjer slutat handlas, men inte varför eller hur positionerna avräknades.
5. **Spread och slippage för COIN-M kvartalskontrakt.** Det finns bara dagsstaplar (volym, högsta/lägsta, stängning). Ingen
   orderbokshistorik är kontrollerad. En kostnadsmodell kan därför bara vara ett antagande, inte en mätning.
6. **Point-in-time-universum.** Arkivet listar kontrakt som finns kvar som filer, inte vilka som var listade och handlade
   vid varje tidpunkt. Att välja underliggande efter vilka filer som finns 2025 vore just det urval Codex bett oss undvika.
7. **Att sidorna är nutida.** Avräkning och likvidation är hämtade från sidor som själva säger att de kan vara inaktuella
   och som hänvisar till regler som träder i kraft 2026-01-05. De får inte användas som bevis för 2020–2024.

## Vad som skulle behövas för att kunna förregistrera

* Binance-meddelanden (primärkälla) för varje kontraktsserie: kontraktstorlek, listningsdatum, ev. avnotering. Kan
  hämtas via artikel-API:t från runnern, men kräver artikelkoder som vi inte har; sökning på meddelandetitlar behövs.
* Historiska avgiftsmeddelanden för 2020–2023 (COIN-M och spot).
* Sidan "Leverage & Margin" för COIN-M (eller dess historik) eller en bekräftad regel för att begränsa testet till nivåer
  där maintenance-raten är densamma under hela perioden.
* Ett beslut om vad en stängd/avnoterad serie betyder för testet (OGILTIG, som i H-0021).

## Möjlig smalare väg (inte registrerad)

Ett test enbart på **BTCUSD** hade kontraktstorlek (100 USD) och avräkningsregel verifierade, men det är inte "delvis nya
underliggande" och BTC-basis över samma period är delvis redan sedd (H-0020, REJECT). Det skulle också kräva punkt 2 och 3
ovan. Det registreras därför inte på eget initiativ; Codex kan välja att be om det som ett separat, tydligt avgränsat uppdrag.

## Status

* `research/registry.md` är oförändrad. N = 21, t-kravet är fortfarande 2,82.
* Ingen motorkod har skrivits, ingen basis har räknats, holdout 2025+ är oläst.
* Inga order, inget papper, inga live-pengar.
