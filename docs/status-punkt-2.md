# Punkt 2: insamling av realtidsdata (BTCUSDT spot)

Status 2026-11-01, gren `integrate/punkt-2-marknadsdata` (ovanpå PR #35, inte pushad).
Teknisk beskrivning: [marknadsdata.md](marknadsdata.md).

**Punkt 2 är klar på macOS men inte verifierad på Windows.** Den kan markeras helt klar när
Windows-kontrollen (med de nya Rust-testerna) har gått igenom, och när någon har kört den installerade
appen på Windows en stund.

## Verifierat

| Vad | Hur |
|---|---|
| Logik med mockdata | 31 Rust-tester gröna, tre körningar i rad. De täcker: <br>– överlapp mellan historik och ström; <br>– stängd och pågående stapel; <br>– ms och µs; <br>– trasiga och felordnade meddelanden; <br>– 429/418 med Retry-After; <br>– avbrott och återanslutning mot en lokal WebSocket-server, med ping/pong; <br>– tystnad som ger `stale` och sedan återhämtning; <br>– REST-ikappkörning, omstart med sparad data och sidindelning; <br>– atomiska skrivningar (en hel batch rullas tillbaka); <br>– upprepade körningar, rättelser och bekräftade luckor; <br>– lås mot en andra insamlare; <br>– felaktig konfiguration utan tyst standard; <br>– inga konto-, order- eller nyckeladresser i koden. |
| Motorn läser datan | 5 nya Python-tester (samma `schema.sql` som appen, bara läsning, rätt format). Hela motorn: 71/71. |
| Riktigt nät | `cargo test real_network -- --ignored`: data-api och data-stream nås. 50 stängda staplar, en pågående stapel och ett strömmeddelande kom inom 4 s, följt av ett kontrollerat stopp. |
| Paketerad app (macOS arm64) | `/Applications/TraderGO.app`, startad utan terminal: <br>– `connected` och redo, 1000 stängda staplar utan luckor; <br>– `quality.check` på appens databas: 1000/1000 rader, inga fel; <br>– avslut ger `stopped`, och omstart hämtar bara det som saknas (0 dubbletter); <br>– en andra start ger ingen andra process; <br>– Status-vyn visar läge, mottagningstid och serverns händelsetid. |

## Ändrat men inte verifierat

- **Windows:** `windows-build.yml` kör nu också appens Rust-tester, men den har inte körts. Inget är provat
  på en Windows-dator.
- **Viloläge och nätavbrott på riktigt:** de är testade med mockdata (klockhopp, tystnad, avbrott) men inte
  genom att datorn faktiskt sov eller att nätet togs bort.
- **24-timmarsgränsen och `serverShutdown`:** hanteras i koden och `serverShutdown` tolkas i tester, men
  ingen anslutning har körts i 24 timmar.

## Begränsningar

- Uppvärmningen (1000 staplar) är en standard och ingen garanti: strategins behov räknas ut när en
  strategi körs live.
- Rättelser visas men åtgärdas inte automatiskt.
- Ingen jämförelse mot en andra källa (kontroll 7 i `hamta-data`) ingår i insamlingen.
- Varje dator samlar in själv; ingen gemensam papperssession.

## Inför punkt 3 (diagram och dataflöde i gränssnittet)

- Ett kommando som läser stängda staplar ur databasen (sidindelat), plus händelser för nya stängda staplar
  och uppdaterad live-stapel.
- Ett diagram som tydligt skiljer stängda staplar från den pågående stapeln, och som märker luckor och
  `stale`.
- Bestäm hur Research-rutor (`SIM`/`HISTORIK`) ska visa live-data, utan att blanda in den i frysta tester.
- Universe kan visa `status.json` i sin diagnostikpanel, bara genom att läsa.
