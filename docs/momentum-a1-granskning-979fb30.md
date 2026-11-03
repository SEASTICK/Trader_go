# Codex omgranskning av A1 revision 2 – 979fb30

Datum: 2026-11-03. Granskad revision: `979fb30f483b856d9210be3591101cd0fb3b3b98`. Diffbas: `a7693b7`.
Lokal gren och fjärrgren `claude/momentum-a1` verifierades på samma revision. Fjärr-main är `72107ed` och saknar fortfarande denna dokumentkedja.

**A1 behöver ytterligare två preciseringar före A2.** De fyra ursprungliga fynden är åtgärdade på metodnivå. Ingen motorkod eller verklig historik har prövats; ett godkänt syntetiskt orakel är inte ett godkännande av en framtida implementation.

## Omgranskning av de fyra tidigare fynden

| Tidigare fynd | Besked på 979fb30 |
|---|---|
| Riskavsikt som kan bli köp efter gap | Rättat genom D17 och reduce-only med loggad hold. O14:s q=2 och kostnad=0 vid gap nedåt samt en verklig minskning vid gap uppåt kontrollerade oberoende. |
| Funding flyttad över affären av 60-sekundersregeln | Rättat: bara exakt samtidiga event omfattas av A/B. O16:s +30 sekunder debiterar nya positionen i båda fallen; −30 sekunder gamla. Ny precisering av legacy-ordning behöver dock avgränsas enligt R2-01. |
| Påstått konservativ Sharpe genom lokalt sämre betalning | Rättat: T-regeln och max-valet med/utan likvidation är borttagna. Alla kriterier måste passera i varje scenario i det förutbestämda åttascenariogridet. Det är en känslighetsgrind, ingen bevisad gräns för Sharpe/t. |
| Samma E_after med två definitioner | Rättat: E_trade och E_post är separata faser. Målvikt/cap gäller efter affär, före B-funding; senare fundingdrift tillåts uttryckligen. O5b kontrollerat. |

Marginalmodellen beskrivs nu som en begränsad forskningsmodell, med båda satserna i gridet. DSR-texten i §14 skiljer råa räknemått från verifierade oberoende försök och kalibrerade intervall. Dessa rättningar accepteras för forskningskontraktet; de verifierar inte historiska börsvillkor eller framtida drift.

## R2-01 [P1] L1/L2 får inte flytta en känd öppningsstop efter senare funding

Plats: `docs/momentum-protokoll-A1.md:214–215`, jämfört med den kända gapfyllningen i §11 och §10.2 (rad 276).

L1/L2 sägs gälla ett legacy-konto med ATR-stop i samma stapel som en mellanhändelse. L2 använder då q_old vid funding genom att lägga stop efter händelsen. Ingen regel undantar en stop som redan är känd att fyllas vid öppningen.

Reproduktion med befintliga O8-tal: C=10 000, q=900, long-stop S=95. Kontraktsöppning 00:00 är 94, alltså fylls stoppen där. Efter avgift är kontot platt med kapital 94 464,64. Vid funding 00:00:30, mark_ref=94 och ränta 0,0001 är beloppet **0 i både L1 och L2**. Den generella L2-regeln skulle i stället debitera 900×94×0,0001 = **8,46** på en avslutad position. Den motsäger både exakt tid och att funding gäller faktiskt innehav.

**Krävd precisering:** L1/L2 gäller endast verkligt okänd ordning mellan en intrastapelstop och en mellanhändelse. Redan kända öppningsutgångar, inklusive gapstop, är utförda före senare event och har företräde. Lås också vilken position som används om inträde sker vid stapelns öppning före en senare intrastapelstop; använd inte en äldre position före inträdet. För funding exakt vid öppningen ska den separata A/B-regeln bevaras. Samma princip gäller efter en redan inträffad likvidation: en stängd position återuppstår inte genom L2.

**Orakel som saknas:** gapstop med funding +30 sekunder (0/0 i L1/L2), samma gapstop med funding exakt vid öppningen (ingående q i A, noll i B), samt inträde vid öppningen och verkligt okänd stop/funding-ordning inne i stapeln (nya innehavet i scenariot med stop sist).

## R2-02 [P1] Definiera avkastningen efter total likvidation så att ekonomisk förlust inte blir OGILTIG

Plats: `docs/momentum-protokoll-A1.md:244`, §4:s dagsavkastningskvot och rad 332–333.

Likvidation sätter E=0 och kontot platt till terminal. §4 beräknar däremot varje dagsavkastning som E_end(D)/E_end(D−1)−1, och §13 kräver 1 096 ändliga värden utan borttagning. För en kapitalserie [100 000, 0, 0, 0] blir avkastningen [−1, 0/0, 0/0]. Därmed blir en modellerad totalförlust OGILTIG, trots att likvidation i main uttryckligen ska ge C6=false och ett ekonomiskt REJECT. Även likviderade kontrollkonton behöver fullständiga, jämförbara serier. Detta är en ytterligare lucka som inte fångades i den första granskningen; den är inte introducerad av revision 2.

**Krävd precisering:** lås en uttrycklig absorberande nollkonvention: övergången från positivt kapital till likviderat nollkapital ger −100 % den dagen, följande dagar i just det dokumenterade likvidationstillståndet ger 0 avkastning. Kontot förblir E=C=q=0, utan affärer/funding eller kapitaltillskott. En oförklarad nolla eller negativt kapital får inte tyst normaliseras. Blandningar ska fortfarande räknas från summan av faktiska delkapital; ett överlevande delkonto kan fortsätta. C6 och beslutet ska följa likvidationsflaggan i main, inte ett statistiskt NaN-fel. Detta är en modellkonvention som ska låsas i protokollet före registrering.

**Orakel som saknas:** likvidation mitt i perioden med minst två följande dagar, likvidation på terminaldagen och ett likviderat delkonto i en fortsatt positiv blandning. Stäm av kedjad avkastning mot slutkapital, full längd, ändliga Sharpe/t-indata och ekonomiskt underkännande i main. Inför inte epsilonkapital, framåtfyllning av positiva värden eller filtrering av NaN.

## Mindre textjusteringar i samma rättning

D11 använder ännu uttrycken "full sökhistorik" och "intervallet" trots rättningen i §14. Ändra raden till samma specificerade räknemått/känslighetsvärden som §14. I §2 ska exakta parametrar beskrivas som projektets fasta designval med forskningsstöd för metodfamiljen; källorna bevisar inte just 7/14/28, 60, 10 % och 2 pp. I §10.2 är derivatornas riktning omkastad: trough/peak−1 ökar med trough och minskar med peak när kapitalet är positivt; drawdownens positiva magnitud har motsatt riktning. Konstruktionen med högre peak och lägre trough är fortfarande den avsedda strängare bounden. Dessa textfel är inte separata P1-fynd.

## Körda kontroller

- `python3 scripts/momentum-a1-oracles.py --check`: PASS.
- `python3 research/audits/momentum-a1-cb335ee/review.py --check`: PASS, oförändrad historisk reproduktion. Att gamla motexempel fortfarande går att räkna är inte i sig ett regressionstest av rättningen.
- `python3 research/audits/momentum-a1-979fb30/review.py --check`: PASS. Kontrollerar utvalda korrigerade orakelutfall och reproducerar ovanstående två luckor med syntetiska tal. Resultat i samma katalogs `verification.json`. Ingen motorimplementation används.
- `cd engine && .venv/bin/python -m pytest tests/test_stats.py tests/test_registry_and_experiment.py tests/test_margin_reference.py tests/test_registered_export.py -q -p no:cacheprovider`: **29 godkända**.
- Alla fyra checklistgeneratorer med `--check`: PASS. `git diff --check a7693b7 979fb30`: rent.
- Första granskningsdokumentet och dess reproduktioner är oförändrade mot a7693b7. Diffen innehåller bara de fem uppgivna A1-/statusfilerna.

## Nästa leverans

Claude rättar R2-01/R2-02 och ovanstående text i A1-utkastet, metodtabellen och syntetiska orakel. Bevara båda granskningarna som historik. Redovisa exakt ny commit, diffbas och verifieringar. MOM-A03/MOM-A04 förblir in_progress; MOM-A05 förblir todo. Ingen A2-registrering eller B-implementation före omgranskning. Ingen marknadshistorik, skyddad data, forskningskörning, serverändring, SQL, driftsättning eller release ingår.
