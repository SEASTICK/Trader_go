# Codex granskning av H-0017 leverans C3

Datum: 2026-11-03. Exakt revision: `d77e3535dc9588bc8454c04112223c594fbbd7ff`. Diffbas: `a19a551`. Lokal/fjärr claude/momentum-c3 verifierade på samma hash; arbetskopian var ren före granskningen.

**C3 behöver två avgränsade rättningar före godkännande.** Normala beslut och tidigare godkända moduler passerar verifieringen. Fynden gäller en tillståndskombination och validering av signalkontraktet, inte en ny strategi-/riskregel.

## C3-01 [P2] Skapa ingen terminalavsikt för ett likviderat konto

Plats: engine/traderlab/momentum_risk.py:264–265, i kombination med likvidationsgrenen 237–241.

När ett konto redan är likviderat, eller close-input dokumenterar likvidation i sista stapeln före terminal, sätter step liquidated=True men lägger därefter ovillkorligen till en terminalavsikt. Det bryter både den absorberande nollregeln i protokollets D21 (§4) och modulens dokumentation om inga fler avsikter efter likvidation.

Reproduktion vid 2024-12-31 20:00 UTC: CloseInput har C=q=0 och liquidated=True. Kör step(..., terminal=True). Resultatet är en terminalavsikt med E_decision=None. När den skickas genom modulens dokumenterade fyllningsväg ger fill_intent LedgerError: kapital före affär måste vara >0, fick 0. En legitim ekonomisk totalförlust riskerar därmed att bli ett implementationsfel när terminalen behandlas. Detta inträffar både med state.liquidated redan satt och vid första rapporteringen av likvidation på samma gräns.

**Rättning:** behåll det absorberande likvidationstillståndet även vid terminal. Markera terminalen behandlad/terminated enligt API-kontraktet men skapa ingen handelsavsikt, fill eller extra kostnad. Försök inte reparera detta genom att låta C1 fylla ett nollkonto, sätta ett litet ersättningskapital eller ändra protokollet. Vanliga levande konton ska fortsatt stängas på terminalen med prioritet och kostnad enligt kontraktet.

**Regressioner:** båda ovanstående ordningarna, samt fortsatt likviderat tillstånd över midnatt fram till terminal. Inga återupplivade positioner, ingen fyllning/funding/kostnad för det likviderade kontot. Levande terminalfall och steg-efter-terminal-vakten ska fortfarande fungera. Själva likvidationsbokföringen är fortsatt utanför C3.

## C3-02 [P2] Validera signalens tillgänglighet och version före omtolkning

Plats: engine/traderlab/momentum_risk.py:154–157 och 196–206.

SignalInput.from_row kör bool(row['available']) utan typkontroll. Strängen "False" blir därför True. _signal_ok kontrollerar sanningsvärde men inte boolean-typ, och ignorerar version helt. Med övriga fält s=1, cap=0,5, w_target=0,5 får både en rad med available="False" och en med version="mom-signal/999" en normalavsikt på första öppningen. fill_intent kan sedan köpa på avsikten. Samma rad med riktig bool False avvisas korrekt.

Det betyder inte att den godkända B-modulen idag producerar sådana rader. Felet är att C3:s offentliga adapter och direkta signalväg accepterar ett ogiltigt eller okänt kontrakt som ett giltigt beslutsunderlag, trots dokumenterad avvisning av feltyp/otillgänglig signal och låst kandidatversion.

**Rättning:** validera rå available som boolesk typ innan någon konvertering. Stöd den riktiga numpy-bool som kan komma från B/Pandas, men avvisa text, tal, None och NaN i stället för att sanningskonvertera dem. Verifiera exakt den godkända signalversionen mom-signal/1.0.0. Samma regler ska gälla direkt SignalInput, dataclasses.replace och from_row före ett beslut accepteras. Fel ska ge kontrollerat RiskError utan ny avsikt eller ändrat state. Behåll korrekt bool False som otillgänglig/OGILTIG_DATA, ingen ersättning med platt/full vikt.

Kontrollera även att signalens egna dag-/beslutstider uttryckligen följer UTC-/dagskontraktet; jämlikhet med en UTC-tid bevisar inte att råvärdet har den typen/tidszonen. Detta är samma inmatningsgräns, ingen ny tidsregel.

**Regressioner:** direkt konstruktion och from_row med "False", "True", 0/1, None, NaN och okänd/saknad/feltypad version; efterföljande steg får inte producera avsikt på dessa. Giltiga Python-/numpy-booleans och riktiga B-rader ska fungera oförändrat. Bevara avvisningen av riktig False. Testa giltig signal med exakt den låsta versionen och otillåten signalmetadata via replace.

## Verifierat underlag

- 61 riskprov och totalt **267 signal-/ledger-/funding-/riskprov** passerar.
- Hela motorsviten: **820 tester godkända**, exit 0. Befintlig joblib-varning om fysisk CPU-detektering förekom utan testfel.
- Egen separat referenstabell med **400 syntetiska beslut** (00:00 och mellanliggande gränser, peak, dagskapital, tidigare permanentstopp, dagslås, cap/platt/band och terminalprioritet) stämmer mot C3 för giltiga indata. Den ersätter inte de två kombinations-/kontraktsfallen ovan.
- Egen revisionslåst audit reproducerar båda fynden. För signalfallen visas även att den returnerade normalavsikten kan fyllas till positiv q. För likvidationsfallen visas både ogiltig terminalavsikt och felet i C1-fyllningen.
- Tio tidigare audits, A1-orakel och fyra checklistgeneratorer: PASS. Fryst H-0017-protokoll, register och godkända B/C1/C2 är byte-identiska mot a19a551. Claudes mutationsserie har inte körts om av Codex.
- Kommentarerna om de två ekvivalenta < / <=-mutationerna motsäger inte de granskade float-reglerna. Testernas positiva gränsfall ersätter dock inte signal-/likvidationskombinationerna ovan.

Reproduktion: `engine/.venv/bin/python research/audits/momentum-c3-d77e353/review.py --check`. Skriptet laddar exakta Git-källor, sparar SHA-256 och syntetiska resultat i verification.json. Ingen marknadshistorik eller extern tjänst används.

## Status och handoff

MOM-C02/C03/C04/C05 behålls som in_progress. MOM-C01 och tidigare A/B/C2-godkännanden bevaras eftersom modulerna inte ändrats. **11/40**. C3 är inte godkänd för nästa C-del. Hela C04 och C03 kräver dessutom framtida intrastapel-/eventintegration även efter rättningarna.

Claude utgår från denna granskningskedja, rättar enbart C3-01/C3-02, kompletterar syntetiska regressioner och API-dokumentation och lämnar exakt ny revision/diffbas för omgranskning. Behåll gamla audits och statusunderlag. Ändra inte C1 för att acceptera en terminalfill på likviderat konto. Ingen historik, H-0017-körning, dataaudit/nedladdning, marginalmotor, drift, app, SQL, release eller paper/live ingår. Materiellt nytt kontraktsval ska tas till Codex före kodning.
