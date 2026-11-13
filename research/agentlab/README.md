# Agentlab: multi-agent-forskning (sidoprojekt, utforskande)

Ett litet, fungerande multi-agent-system som genererar tradingidéer, backtestar dem parallellt, **angriper** resultaten, låter en Builder iterera, slänger det som dör och låter en Domare avgöra. Kod: `engine/traderlab/agentlab/`. Körning: `cd engine && .venv/bin/python -m traderlab.agentlab run`.

**Utforskande, inte bekräftande.** Systemet gör många försök på samma data. Inget här är ett test enligt `research/registry.md`, påverkar inte N där och blir aldrig papper på egen hand: `READY_FOR_PAPER` betyder "kandidat", och en formell registrering (`H-xxxx`) och ett färskt test framåt krävs. Inga riktiga pengar eller order. Data: lokala Binance USDⓈ-M-arkiv, bara före 2025 (slutprovet är aldrig läst; `Panel` vägrar data från 2025).

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

## Informationsbarriär och poängsystem

Tre perioder: **discovery** 2020-10 till 2022-12 (Builder får bara se den), **valid** 2023 och **final** 2024 (förseglade; bara Domaren öppnar dem, och bara för kandidater som överlevt discovery; slutåret öppnas bara efter godkänd validering). Alla backtester körs med kostnad (10 bp per sida), finansieringsränta och beslut på stängd dag, fyllning vid nästa öppning.

Poäng 0–100, vikter i `judge.WEIGHTS`: efter-kostnad-avkastning 12, Sharpe 15, max drawdown 8, stabilitet över perioder 10, stabilitet över tillgångar 8, omsättning 5, kostnadskänslighet 12, parameterkänslighet 8, diversifieringsvärde 7, evidenskvalitet 15 (permutationstest, deflated Sharpe, ingen läckage, tillräckligt urval). **Hårda krav (REJECT oavsett poäng):** läckage, discovery-Sharpe ≤ 0,3, olönsam med 2,5× kostnader, slumptest p > 0,15, deflated Sharpe < 0,5, negativ validering. Därefter: poäng < 40 REJECT, 40–55 MORE_RESEARCH, ≥ 55 PROMISING (v2: kräver också valideringsårets Sharpe ≥ 0,5). READY_FOR_PAPER kräver dessutom bra slutår, p ≤ 0,02, deflated Sharpe ≥ 0,9, låg beta eller slår baslinjen, och diversifierande. **Deflated Sharpe** räknas med **effektivt antal oberoende försök** (deltagandekvoten för korrelationsmatrisen av alla försöks avkastningsserier), så att tio varianter av samma idé inte räknas som tio oberoende.

Negativa kontroller (slumpstrategier) går genom samma pipeline varje körning; en passerad kontroll vore ett larm om falska positiva.

## Experimentregister och omdömning

`experiments.jsonl` är append-only. Varje post har hypotes, parametrar, modell, features, data, tidsram, marknad, resultat (discovery, grannar, baslinjer), kostnader, risk, adversariella mått, agenternas kommentarer, domslut och domarversion. Äldre domar ändras aldrig: `python -m traderlab.agentlab rejudge` lägger till nya rader (`stage: rejudge`) när domarregeln ändras, utan att öppna ny förseglad data. Alla idéer som testas får en post, så forskningshistoriken kan läsas i efterhand.

## Första autonoma körningen (R001–R004, 2026-11-13)

Fyra körningar i rad på de lokala USDⓈ-M-perparna (119 kontrakt, dagliga staplar, bara före 2025). Rapporter: `runs/R00x/report.md`, GitHub-sammanfattning: `outbox/`.

| Mått | Värde |
|---|---|
| Idéer genererade av Idé-agenten | **650** (150 + 150 + 150 + 200) |
| Utvalda och testade (rankade, bredd först) | **126**, plus **14** Builder-mutationer = **140** versioner |
| Negativa kontroller (slump) | 32, **0** gick vidare |
| **REJECT** | **125** (122 vid discovery, 3 vid förseglad validering) |
| **MORE_RESEARCH** | **1** (`ensemble_rank` xs_mom + funding_carry + lowvol, q=0,3, rebal 3) |
| PROMISING / READY_FOR_PAPER | **0** / **0** |
| Sub-agenter som skapades | 499 (tillfälliga, i 4 körningar) |
| Försök som räknas (inklusive grannparametrar) | 770, effektivt oberoende ca 13 till 16 |
| Tid | 184 s för alla fyra körningar (4 processer) |

**Vad systemet lärde sig**
* **Discovery håller inte.** De fyra som överlevde discovery (Sharpe 1,65–1,74 efter kostnad, tål 2,5× kostnader, permutation p 0,003–0,017) föll i det förseglade valideringsåret 2023: Sharpe 0,29 (ensemble_rank), −1,56 (LightGBM), −0,50 (ensemble_rank q=0,2) och −1,91 (bab). Den enda som klarade validering hade 0,58 under slutåret 2024. Kanten i discovery var till stor del anpassning till 2020–2022.
* **ML slog den enkla tumregeln xs_mom i 2 av 13 jämförelser**, med hög omsättning. Det enkla får vara kvar.
* **Trend, ts_mom och Donchian** går inte att skilja från slump (BTC-driften dominerar), **funding_carry ensamt** (22 testade) fick inga överlevare, och fem familjer (pairs, xs_rev, funding_fade, vol_shock, mtf_trend) kom aldrig över discovery-Sharpe 0,9.
* Vanligaste dödsorsaker: inte skild från slumpen, olönsam med 2,5× kostnader, deflated Sharpe.

**Buggar och problem som körningen och testerna avslöjade (alla rättade)**
1. **Finansieringsräntan var inpassad en 8-timmarsslot för optimistiskt** (00:00-utbetalningen vid inträdet räknades). Den första körningens enda PROMISING-kandidat försvann efter rättningen: ett exempel på att ett bra resultat var en artefakt.
2. `pairs` kraschade (`for a, b in` över tretal) och `hold=1` gav `ffill(limit=0)`. Hittades av körningen respektive ett rökprov över alla familjer.
3. **Deflated Sharpe räknade korrelerade varianter som oberoende** och dödade allt. Ersatt med effektivt antal oberoende försök.
4. **Läckagetestet var blint för en dags framtidsblick** (jämförde för tidiga rader). Rättat och testat med en avsiktligt läckande strategi.
5. **Domare v1 var för snäll**: PROMISING med valideringsår 0,29. v2 kräver valideringsår ≥ 0,5; gammal dom omdömdes med `rejudge` (ny rad, ingen ny förseglad blick).

**Kända begränsningar:** survivorship (bara kontrakt med lokala arkiv), dagliga staplar och inget intradagsutförande, inga open interest-, orderboks- eller makrodata (föreslagna källor, se `data.py`), inga LSTM/GRU/transformers (kräver torch), validerings- och slutåret är nu delvis "förbrukade" för dessa familjer (5 blickar), och permutationstestet jämför timing mot en cirkulärt förskjuten version av samma vikter.

**Nästa rationella förbättring:** gör valet inne i en rullande walk-forward (nästlad urvalssteg) i stället för en fast discovery/validering, så att varje år blir out-of-sample, och lägg in open interest och dagliga `metrics` från data.binance.vision som ny källa. Familjen `ensemble_rank` (momentum + funding + low-vol) är den enda som är värd en andra titt, med ett punkt-i-tid-universum.
