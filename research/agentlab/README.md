# Agentlab: multi-agent-forskning (sidoprojekt, utforskande)

Ett litet, fungerande multi-agent-system som genererar tradingidéer, backtestar dem parallellt, **angriper** resultaten, låter en Builder iterera, slänger det som dör och låter en Domare avgöra. Kod: `engine/traderlab/agentlab/`. Körning: `cd engine && .venv/bin/python -m traderlab.agentlab run`.

**Utforskande, inte bekräftande.** Systemet gör många försök på samma data, och valideringsåret 2023 och slutåret 2024 är förbrukade (se nedan). Inget här är ett test enligt `research/registry.md`, påverkar inte N där och blir aldrig papper på egen hand: `READY_FOR_PAPER` betyder "kandidat", och en formell registrering (`H-xxxx`) och ett färskt test framåt krävs. Inga riktiga pengar eller order. Data: lokala Binance USDⓈ-M-arkiv, bara före 2025 (slutprovet är aldrig läst; `Panel` vägrar data från 2025).

## Agenter (`agents.py`, `judge.py`, `orchestrator.py`)

| Agent | Mål | Kan skapa sub-agenter |
|---|---|---|
| **Orchestrator** | Delar upp mål i uppgifter, startar agenter parallellt, samlar resultat, avgör vilka som behöver en ny runda | startar alla |
| **Idé** | Genererar många rimliga idéer (15 familjer: momentum, reversion, trend, tvärsnitt, carry/funding, volatilitet, parhandel, regim, anomali, multi-tidsram, ensembler, ML) | |
| **Data** | Kontrollerar vilken data som finns, bygger features, föreslår nya källor (pluggbara med `register_source`) | FundingSpecialist, OrderbookSpecialist, OISpecialist |
| **Quant (Builder)** | Försöker hitta edge: implementerar, backtestar, jämför parametergrannar och baslinjer | CrossSectionSpecialist, PairsSpecialist |
| **ML** | LightGBM, ridge, random forest, MLP, ensemble, sannolikhetsmodell, walk-forward, jämför mot enkla baslinjer | |
| **Kostnad/Utförande** | Försöker göra strategin olönsam: kostnadsrutnät 0–5×, break-even, en dags fördröjning, finansiering | |
| **Risk** | Letar situationen där den går sönder: drawdown, CVaR, koncentration, regimer, beta | LiquidationStressSpecialist |
| **Skeptiker** | Försöker visa att edgen inte finns: permutationstest, deflated Sharpe, halvårs- och tillgångsstabilitet | LeakageSpecialist, AssetSplitSpecialist |
| **Portfölj** | Korrelation, diversifieringsvärde, okorrelerade kombinationer | |
| **Domare** | Gemensamt poängsystem och domslut | |

Neurala nät utöver sklearns MLP (LSTM/GRU/temporal CNN/transformer) kräver `torch`, som inte är installerat. ML-agenten hoppar över saknade bibliotek och redovisar det.

## Kommunikation, uppgifter och sub-agenter

* **Blackboard** (`state.py`, `research/agentlab/state.json`): litet gemensamt tillstånd. Agenterna får en kompakt `view()` (antal försök, bästa kandidater, senast avvisade, familjestatistik, datatillgång, kända problem, öppna uppgifter), aldrig hela historiken. Bara Orchestratorn skriver.
* **Uppgiftskö** (`TaskQueue`): prioritet och beroenden. `ready()` ger alla uppgifter med klara beroenden, och de körs **parallellt** i en processpool (en arbetsprocess per uppgift, delad panel, delad viktcache på disk). För varje idé går Quant, Kostnad, Risk och Skeptiker iväg samtidigt (ML bygger först vikterna).
* **Sub-agenter**: en agent lägger en `spawn`-begäran i sitt resultat (`{name, goal, fn, payload}`). Orchestratorn startar sub-agenten som en ny uppgift med ett eget mål, och den försvinner när den är klar (`ephemeral` i blackboarden). Exempel: Risk → LiquidationStressSpecialist, Skeptiker → LeakageSpecialist.
* **Debatt**: varje agent skickar invändningar `{code, severity, agent, text, mutable}` till Builder (loggade i `messages.jsonl`). Builder svarar med en bestämd mutation per invändningstyp (`mutate`: dyr omsättning → längre rebalansering, svans → vol-målsättning, parameterinstabilitet → större lookback, ML-overfit → ridge, regimkänslighet → regimfilter). Den nya versionen attackeras på nytt. Dör idén (inga rimliga ändringar kvar, eller max 2 iterationer) går systemet vidare.
* **GitHub**: `channel="github"`-meddelanden samlas i `outbox/github-R00x.md` som kan postas som PR-kommentar (så gjorde jag). Idéer utifrån (till exempel från Codex eller en människa via en kommentar) läggs som rader i `inbox/ideas.jsonl` och prövas på samma villkor.

## Informationsbarriär (verklig, från R005) och förbrukad data

Tre perioder: **discovery** 2020-10 till 2022-12, **valid** 2023, **final** 2024. Barriären är byggd i koden, inte bara i vad som visas:
* **Discovery-agenter får en panel som slutar 2022-12-31** (`agents._view`, `agents.panel()`). Quant, ML, Kostnad, Risk, Skeptiker, Portfölj och alla sub-agenter ser aldrig 2023 eller 2024, och `quant_task` returnerar inga framtida mått. Portföljagenten räknar kombinationer bara på discovery.
* **Valideringsåret beräknas i ett eget steg** (`validate_task`) efter discovery-grinden, med en panel som slutar 2023-12-31 (2024 finns inte där). **Slutåret beräknas i ett annat eget steg** (`final_task`) och bara för dem som klarat valideringsgrinden. Inga framtida mått går tillbaka till Builder eller urvalet.
* Test med en avsiktlig **framtidsmarkör** (`tests/test_agentlab.py`): värden efter discovery ersätts med en markör, och discovery-uppgifternas resultat är oförändrade. Samma för valideringssteget (2024). Ett test visar att slutsteget aldrig körs när valideringen misslyckas, och att barriären faktiskt slår i testet om den stängs av.

**Förbrukad, utforskande data.** R001–R004 byggdes *innan* barriären fanns i koden: alla arbetsprocesser hade hela panelen och 2023/2024 beräknades för **alla** deras kandidater (bara visningen var begränsad). Valideringsåret och slutåret är därför **förbrukade** för alla R001–R004-kandidater, och inga av deras utfall är ett orört prov. Det är markerat i `state.json` (`legacy_unsealed`, `data_status`) och återställs aldrig av koden. Nya körningar loggar varje avslöjande i `spent`, och även de förbrukar data: upprepade körningar mot samma år gör att 2023 och 2024 aldrig blir ett bekräftande prov för dessa familjer.
**Valda efter utfall.** Deflated Sharpe med effektivt antal försök och domare v2 (valideringsår ≥ 0,5) valdes *efter* att utfall setts. De kan inte retroaktivt bekräfta en kandidat; `ensemble_rank`-kandidatens status (MORE_RESEARCH) är därför en utforskande markering, inte ett resultat. Alla backtester körs med kostnad (10 bp per sida), finansieringsränta och beslut på stängd dag, fyllning vid nästa öppning.

## Datatäckning: audit av R001–R004 och motorregel v2

Codex granskning visade att motorn tyst gjorde okänd data till noll: finansiering saknades för 34 av 119 kontrakt (bara 85 har finansieringsarkiv) och ifylldes med `0.0`, och en saknad nästa öppningskurs blev `fillna(0.0)`. **Audit av redan förbrukad data** (`python -m traderlab.agentlab audit`, `audits/coverage-R001-R004.json`, de gamla experimentposterna är oförändrade). Vikterna för alla 148 kandidater återskapades med den gamla regeln och **alla 148 återgav registrets discovery-Sharpe exakt**, så auditen är trogen. Exponering = summa av |vikt| över alla dagar och instrument:

| Mått (alla 148 kandidater, hela 2020–2024) | Andel av bruttoexponeringen |
|---|---|
| Okänd finansiering (saknat arkiv eller dag utan utbetalning) | **0,76 %** (22 kandidater över 1 %, högst 10,8 %) |
| Blockerad: ingen öppningskurs vid fyllningen (t+1) | 0,34 % |
| Datalucka i utträdespriset, senare pris finns (till exempel arkivhålet 2022-02-26–28) | 0,05 % |
| Okänt utträde utan senare pris (avnotering, utgången leverans) | 0,02 % |
| **Allt okänt tillsammans** | **0,90 %** (median 0,70 % per kandidat, högst 11,4 %, `pairs` värst; 30 kandidater över 1 %) |

De fyra som överlevde discovery hade 0,7–1,3 % okänd exponering (finansiering 0,6–1,1 %, pris 0,1–0,4 %). **Effekt på discovery-Sharpe** när samma vikter körs med motor v2 i stället för tyst noll: i snitt −0,17 (−0,81 till +0,26; sjunker för 109, stiger för 32): `ensemble_rank` 1,74 → 1,44, `ml_xs` 1,65 → 1,37, `ensemble_rank` (q=0,2) 1,71 → 1,40, `bab` 1,70 → 0,93. Det ändrar ingen dom och ger **ingen retroaktiv PROMISING eller READY_FOR_PAPER**. R001–R004 är fortfarande förbrukad, utforskande data.

**Ett annat fel som auditen hittade:** USDⓈ-M-katalogen innehåller **leveranskontrakt** (`BTCUSDT_220930`, `_230331`, `_230630`, `_240628`, `_240927`) som R001–R004 behandlade som evighetsterminer (de går ut och har ingen finansiering). 99 av 148 kandidater hade exponering mot dem (i snitt 0,5 %, högst 2,2 % av exponeringen).

**Motorregel v2 (vald efter att de första utfallen och auditen setts, inte förregistrerad för R001–R004; gäller från och med nu):**
1. **Universum:** ett instrument får bara handlas dag t om finansieringsutbetalningar fanns för minst 5 av de 7 dagarna *före* t (`Panel.universe`, `funding_rule`). Dag t:s hink innehåller utbetalningen vid t+1 00:00, som sker först efter beslutet, så den används inte (shift 1; gränstest ändrar bara den hinken och visar att universum och vikter till och med t är oförändrade). Det utesluter kontrakt utan finansieringsarkiv och leveranskontrakt, och inget fylls längre med 0.
2. **Körbarhet:** inget pris vid fyllningen (öppning t+1) betyder att positionen inte kan öppnas eller hållas: vikten blir noll och exponeringen mäts (`blocked`).
3. **Utträdespris:** saknas öppning t+2 men ett senare pris finns inom 5 dagar värderas positionen mot det (en datalucka; mäts som `gap_filled`). Finns inget senare pris (avnotering, utgången leverans) räknas det som en förlust på positionens vikt, oavsett long eller short (`MISSING_PRICE_LOSS`), aldrig noll och aldrig en vinst.
4. **Finansiering:** okänd finansiering under en hållen position debiteras 0,3 % per dag och exponeringsenhet, alltid till nackdel (`FUNDING_PENALTY`).
5. **Ogiltigt:** om mer än **1 %** av bruttoexponeringen vilar på okänd data (blockerad, okänt utträde eller okänd finansiering) är utvärderingen **OGILTIG** (`CoverageInvalid`): kandidaten får domen OGILTIG, aldrig REJECT, aldrig en poäng och aldrig ett slutsteg. `penalize=False` återger den gamla motorn och används bara av auditen.
**Valda efter utfall:** 1 %-gränsen, 0,3 %-straffet, −100 %-förlusten, 5-av-7-regeln och 5-dagarsgränsen för luckfyllnad valdes efter att de första utfallen och auditen setts. De är inte förregistrerade för R001–R004 och kan inte retroaktivt bekräfta eller dömma om något gammalt resultat. De är konservativa antaganden (en övre gräns, inte en uppskattning av det verkliga utfallet) och ändras inte efter nya utfall. **Auditen ovan gäller den gamla motorn:** vikterna är återskapade med den gamla universumregeln (`funding_rule=False`) och jämförs med `penalize=False` (tyst noll); bara kolumnen "med motor v2" tillämpar luckfyllnad, blockering och avgifter på de gamla vikterna, och universumregeln ingår inte där.

## Historiskt universum (punkt i tid)
Från och med universumsauditen läser Agentlab bara USDT-perpar, ur en panel med alla arkivlistade perpar (396 mot 119 i R001–R004), och universumet är en regel som bara använder data till och med beslutsdagen (`universe.py`, `universe_at`). Leveranskontrakt (`BTCUSDT_230331`) räknades som perpar i R001–R004. Se [universe/README.md](universe/README.md) och [rapporten](universe/coverage-discovery.md). Domaren nekar `PROMISING` om arkivlistan (2020–2024) visar perpar eller månader som saknas i panelen, även vid cacheträff, eller om täckningen är okontrollerad. R001–R004 är oförändrade och exploratoriska: 24 % (2022) till 47 % (2024) av deras bruttoexponering låg utanför ett korrekt universum.

## Poängsystem

Poäng 0–100, vikter i `judge.WEIGHTS`: efter-kostnad-avkastning 12, Sharpe 15, max drawdown 8, stabilitet över perioder 10, stabilitet över tillgångar 8, omsättning 5, kostnadskänslighet 12, parameterkänslighet 8, diversifieringsvärde 7, evidenskvalitet 15 (permutationstest, deflated Sharpe, ingen läckage, tillräckligt urval). **Hårda krav (REJECT oavsett poäng):** läckage, discovery-Sharpe ≤ 0,3, olönsam med 2,5× kostnader, slumptest p > 0,15, deflated Sharpe < 0,5, negativ validering. Därefter: poäng < 40 REJECT, 40–55 MORE_RESEARCH, ≥ 55 PROMISING (v2: kräver också valideringsårets Sharpe ≥ 0,5). READY_FOR_PAPER kräver dessutom bra slutår, p ≤ 0,02, deflated Sharpe ≥ 0,9, låg beta eller slår baslinjen, och diversifierande. **Deflated Sharpe** räknas med **effektivt antal oberoende försök** (deltagandekvoten för korrelationsmatrisen av alla försöks avkastningsserier), så att tio varianter av samma idé inte räknas som tio oberoende.

Negativa kontroller (slumpstrategier) går genom samma pipeline varje körning; en passerad kontroll vore ett larm om falska positiva.

## Experimentregister och omdömning

`experiments.jsonl` är append-only. Varje post har hypotes, parametrar, modell, features, data, tidsram, marknad, resultat (discovery, grannar, baslinjer), kostnader, risk, adversariella mått, agenternas kommentarer, domslut och domarversion. Äldre domar ändras aldrig: `python -m traderlab.agentlab rejudge` lägger till nya rader (`stage: rejudge`) när domarregeln ändras, utan att beräkna någon ny 2023/2024-data. Alla idéer som testas får en post, så forskningshistoriken kan läsas i efterhand.

## Första autonoma körningen (R001–R004, 2026-11-13)

**Obs:** R001–R004 körde med en barriär som bara begränsade vad som visades, inte vad som beräknades (se Informationsbarriär). Deras 2023/2024-utfall är förbrukad, utforskande data. Fyra körningar i rad på de lokala USDⓈ-M-perparna (119 kontrakt, dagliga staplar, bara före 2025). Rapporter: `runs/R00x/report.md`, GitHub-sammanfattning: `outbox/`.

| Mått | Värde |
|---|---|
| Idéer genererade av Idé-agenten | **650** (150 + 150 + 150 + 200) |
| Utvalda och testade (rankade, bredd först) | **126**, plus **14** Builder-mutationer = **140** versioner |
| Negativa kontroller (slump) | 32, **0** gick vidare |
| **REJECT** | **125** (122 vid discovery, 3 vid valideringsåret) |
| **MORE_RESEARCH** | **1** (`ensemble_rank` xs_mom + funding_carry + lowvol, q=0,3, rebal 3) |
| PROMISING / READY_FOR_PAPER | **0** / **0** |
| Sub-agenter som skapades | 499 (tillfälliga, i 4 körningar) |
| Försök som räknas (inklusive grannparametrar) | 770, effektivt oberoende ca 13 till 16 |
| Tid | 184 s för alla fyra körningar (4 processer) |

**Vad systemet lärde sig**
* **Discovery håller inte.** De fyra som överlevde discovery (Sharpe 1,65–1,74 efter kostnad, tål 2,5× kostnader, permutation p 0,003–0,017) föll i valideringsåret 2023 (som redan var förbrukat, se ovan): Sharpe 0,29 (ensemble_rank), −1,56 (LightGBM), −0,50 (ensemble_rank q=0,2) och −1,91 (bab). Den enda som klarade validering hade 0,58 under slutåret 2024. Kanten i discovery var till stor del anpassning till 2020–2022.
* **ML slog den enkla tumregeln xs_mom i 2 av 13 jämförelser**, med hög omsättning. Det enkla får vara kvar.
* **Trend, ts_mom och Donchian** går inte att skilja från slump (BTC-driften dominerar), **funding_carry ensamt** (22 testade) fick inga överlevare, och fem familjer (pairs, xs_rev, funding_fade, vol_shock, mtf_trend) kom aldrig över discovery-Sharpe 0,9.
* Vanligaste dödsorsaker: inte skild från slumpen, olönsam med 2,5× kostnader, deflated Sharpe.

**Buggar och problem som körningen och testerna avslöjade (alla rättade)**
1. **Finansieringsräntan var inpassad en 8-timmarsslot för optimistiskt** (00:00-utbetalningen vid inträdet räknades). Den första körningens enda PROMISING-kandidat försvann efter rättningen: ett exempel på att ett bra resultat var en artefakt.
2. `pairs` kraschade (`for a, b in` över tretal) och `hold=1` gav `ffill(limit=0)`. Hittades av körningen respektive ett rökprov över alla familjer.
3. **Deflated Sharpe räknade korrelerade varianter som oberoende** och dödade allt. Ersatt med effektivt antal oberoende försök.
4. **Läckagetestet var blint för en dags framtidsblick** (jämförde för tidiga rader). Rättat och testat med en avsiktligt läckande strategi.
5. **Domare v1 var för snäll**: PROMISING med valideringsår 0,29. v2 kräver valideringsår ≥ 0,5; gammal dom omdömdes med `rejudge` (ny rad, ingen ny beräkning av 2023/2024).

**Kända begränsningar:** survivorship (bara kontrakt med lokala arkiv), dagliga staplar och inget intradagsutförande, inga open interest-, orderboks- eller makrodata (föreslagna källor, se `data.py`), inga LSTM/GRU/transformers (kräver torch), validerings- och slutåret är **förbrukade** för alla R001–R004-kandidater (barriären var då bara en visningsregel), och permutationstestet jämför timing mot en cirkulärt förskjuten version av samma vikter.

**Nästa rationella förbättring:** gör valet inne i en rullande walk-forward (nästlad urvalssteg) i stället för en fast discovery/validering, så att varje år blir out-of-sample, och lägg in open interest och dagliga `metrics` från data.binance.vision som ny källa. Familjen `ensemble_rank` (momentum + funding + low-vol) är den enda som är värd en andra titt, med ett punkt-i-tid-universum.
