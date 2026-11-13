# Punkt-i-tid-universum och datatäckning (Binance USDⓈ-M perpetuals)

Underlag för frågan: har nästa Agentlab-körning ett *trovärdigt historiskt universum*? Kod: `engine/traderlab/agentlab/universe.py` (regel och `universe_at`), `universe_listing.py` (arkivlistan), `universe_audit.py` (rapporten). Tester: `engine/tests/test_universe.py`.
Rapport: [coverage-discovery.md](coverage-discovery.md) (läsbar) och `coverage-discovery.json` (alla tal, per kandidat och per symbol). Regenerera: `python -m traderlab.agentlab universe-audit` (kräver lokala rådata, ingen ny nätåtkomst).

## Källa och vad den kan och inte kan
- **Källa:** den öppna bucketen bakom data.binance.vision (S3-listning av filnamn). Binance REST (`exchangeInfo`) svarar 451 härifrån och kringgås inte. Det finns alltså **ingen officiell historisk kontraktslista med listnings- och avnoteringsdatum**; listningen härleds ur arkivet (vilka dagsfiler som finns), vilket är exakt det som kan hämtas och testas.
- `um-listing.json` = per symbol vilka månader som har 1d-staplar och finansiering, bara till och med 2024-12 (filnamn från 2025 sparas aldrig, ingen data därifrån öppnas). Hämtad 2026-11-13 (396 USDT-perpar med arkiv före 2025). Regenerera: `python -m traderlab.agentlab.universe_listing research/agentlab/universe/um-listing.json` (nät krävs).
- **Listning/avnotering = första/sista stapel.** Första stapeln ≈ listning, sista stapeln ≈ avnotering. Dagen för en avnotering kan inte skiljas från ett arkivhål i realtid, så båda ger "ingen stapel idag" = ohandlingsbart (inget fylls i). Efterhandsrapporten räknar hålen separat (§3).
- **Perp eller leverans, verifierbart:** namn `SYMBOL_YYMMDD` = leveranskontrakt (utgångsdatum i namnet; sista dagsstapeln ligger på utgångsdatumet eller högst 2 dagar efter, 32 av 32 kontrollerade); inga leveranskontrakt har finansieringsarkiv och alla 396 USDT-perpar har det. `*SETTLED` är efterhandsnamn på avnoterade kontrakt. BUSD/USDC-perpar och övriga produkter ligger utanför omfånget (men redovisas; alla BUSD-perpar listade senast 2022-12 har även en USDT-perp på samma underliggande).
- **Index-perpar** (t.ex. `BTCDOMUSDT`) kan inte skiljas från vanliga perpar med arkivets metadata. De ingår som USDT-perpar (de var handlingsbara).

## Regeln (`Panel.universe`, anropas av alla Agentlab-uppgifter; `universe_at(panel, t)` är dess punkt-i-tid-vy)
Ett kontrakt är handlingsbart dag *t* om: det är en USDT-perp (omfång v3), har en stapel dag *t*, minst 90 staplar bakåt, finansiering känd för minst 5 av de 7 dagarna före *t* (regel v2), och rankas bland topp 30 efter 30 dagars median omsättning till och med *t*. Bara data till och med *t* används (testat: universum dag *t* är oförändrat om allt efter *t* tas bort). Avnoterade kontrakt finns kvar fram till sin sista stapel; kontrakt som inte börjat finns inte. Inget härleds ur dagens lista.

## Vad som ändrats för framtida körningar
- `load_um_panel` läser nu bara USDT-perpar (leveranskontrakt, `*SETTLED`, BUSD/USDC läses inte in).
- **Täckningsgrind (regel):** `universe_gap(panel, listing)` jämför den aktuella arkivlistan med det panelen faktiskt innehåller, för alla USDT-perpar och alla listade månader 2020-01..2024-12: `SYMBOL` = perp som saknas helt, `SYMBOL@YYYY-MM` = listad månad utan en enda stapel. Den körs **vid varje inläsning, även vid cacheträff**, och en gammal cache kan därför inte ge godkänt läge. Resultatet ligger i `panel.meta["universe_gap"]` (lista) och `["universe_gap_checked"]`.
- **Konsekvens:** en icke-tom lucklista, eller en panel inläst utan arkivlista (okontrollerad), gör att Domaren nekar `PROMISING` (och därmed `READY_FOR_PAPER`, som bara kan komma ur `PROMISING`): utfallet blir `MORE_RESEARCH` med anteckning om luckorna. `data_task` rapporterar luckorna i `state.json`. Syntetiska paneler (tester) har ingen grind. Idag är luckan **0** (alla arkivlistade USDT-perpar och månader är nerladdade och checksummeverifierade; panelen v3 har 396 symboler mot 119).
- `Panel.scope_rule` (standard på) styr omfånget; `scope_rule=False` + `funding_rule=False` återskapar universumet i R001-R004 (används av `audit.py`).
- R001-R004 och `research/agentlab/experiments.jsonl` är **oförändrade** och förblir exploratoriska. Inget 2025+ har öppnats och ingen ny hypotes har körts.

## Resultat i korthet (detaljer i rapporten)
- Månadsfiler: 0 av 9 706 listade USDT-perp-symbolmånader (2020-2024) saknas lokalt. Före denna PR saknades 81 av 166 perpar som fanns före 2023 (och alla senare) och tidiga 2020-månader för äldre symboler.
- Arkivhål på dagsnivå: 273 symboldagar 2022 (0,5 %; främst två datum då ~48 perpar saknar stapel: 2022-02-26..28 och 2022-04-01..02) och 50 symboldagar 2023; övriga år 0. Finansieringsarkivet saknar stapelmånader hos 7 perpar (1-1,7 % av symbolmånaderna 2021-2022).
- Universumet R001-R004 kunde välja jämfört med punkt-i-tid-universumet: 7 % av de gamla platserna 2020-2021, 19,7 % 2022, 35,7 % 2023 och 49,5 % 2024 låg utanför (främst för att kontrakt som panelen saknade rankades före). Leveranskontrakt stod för 35 platser 2022, 17 år 2023 och 193 år 2024.
- Bruttoexponeringen i R001-R004 utanför ett korrekt universum: 5 % (2020), 13 % (2021), 24 % (2022), 36 % (2023), 47 % (2024); 112 av 148 kandidater hade över 5 % utanför, 99 hade någon exponering mot leveranskontrakt. Av det är 26,4 % av total bruttoexponering "bortrankad av kontrakt som panelen saknade", 0,6 % leveranskontrakt, 0,1 % okänd finansiering. Slutsats: R001-R004 hade ett **inte trovärdigt** historiskt universum och förblir exploratoriska.

## Kvarstående begränsningar (blockerar bekräftande påståenden tills de är lösta eller accepterade)
1. Ingen officiell listnings-/avnoteringshistorik: datumen är observerade första/sista staplar. Ett kontrakt som listats men aldrig fått en arkivfil syns inte (arkivet är då den enda källan).
2. Arkivhål (§3) är bara kvantifierade, inte lagade. Dagar utan stapel är ohandlingsbara; en strategi som hade en position när hålet uppstod värderas enligt motorregel v2 (nästa öppning inom 5 dagar, annars −100 %).
3. Index-perpar och rebrands (symbolbyten som `BNX`/`SETTLED`-kontrakt) behandlas som egna kontrakt; vi korrigerar inte för namnbyten.
4. Åren 2023 och 2024 (valid/final) är redan förbrukade; universumsrapporten för dem är en efterhandskontroll, inte ett nytt test.
