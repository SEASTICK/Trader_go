# Momentummodell – implementationskontrakt, utkast 0.1

Datum 2026-11-03. Underlag: forskningsplan f43c1e7 och momentum-metodgranskning-20261103.md. Status: GRANSKNINGSUTKAST till Claude, inte förregistrerat eller godkänt för implementation/körning. H-0013 och H-0016 är oförändrade. Siffrorna för modell och risk kommer från den godkända arbetsinriktningen; preciseringarna nedan är nya förslag som ska låsas före registrering, inte efter resultat.

## K01. Identitet och omfattning

En huvudmodell: BTCUSDT USDⓈ-M, long/platt, momentumsignaler 7/14/28 kalenderdagar, lika vikt. Dagliga enkla avkastningar, rullande 60 värden med ddof=1 och annualisering sqrt(365). Målvikt s×min(1,0,10/vol). Alla horisonter måste finnas. Ogiltig/icke-positiv volatilitet eller otillräcklig uppvärmning ger signalstatus unavailable, ingen division med noll och ingen ny position.

Ingen parameteroptimering, short, ATR-stop, take-profit, regimväljare eller ML i huvudmodellen. Short och befintliga ATR-stop får finnas i de uttryckligen definierade gamla kontrollstrategierna. Detta ändrar inte huvudmodellens mandat.

Versionsmärk signal-, utförande-, resultat- och protokollkontrakt. Registreringen ska identifiera den exakta frysta versionen. Ingen modell får köra under H-0013:s jobbkontrakt.

## K02. Tid och horisont

- Stapelindex är öppningstid i UTC, intervallet [t,t+4h). Dess close är känd först vid t+4h.
- Dag D kräver exakt staplarna 00,04,08,12,16,20 och är känd först vid D+1 00:00. Dagsclose är 20-stapelns close, inte dess open.
- C_D/C_(D−h)−1 > 0 ger delsignal 1; lika pris ger 0. En 60-dagars volatilitet kräver 61 kompletta dagsstängningar.
- Första testöppning: 2022-01-01 00:00 UTC, före handel kapital 100 000 och q=0. Den första dagsavsikten kan använda 2021-12-31:s just stängda dag. Det är uppvärmningsdata, inte en position före testet.
- Sista tillåtna fyllning: 2024-12-31 20:00 UTC, känd i förväg. Stäng allt vid denna öppning med kostnad och gör inga nya köp där. Alla återstående punkter fram till exklusivt 2025-01-01 redovisas platt. Ingen 2025-stapel öppnas.
- Sex halvår är enbart rapportgrupper. Positioner, kapital, högvattenmärke och permanent stopp nollställs aldrig.
- Interna kapitalvärden har tidpunkt och eventfas. En points värde märks inte med en tidigare stapelöppning om den beror på senare close/open. Där flera event delar tid skiljs startkapital, före och efter utförande åt.
- Statistik får en startpunkt före första kostnaden. Dagsavkastning ska multipliceras från kapitalförändringar tillhörande rätt UTC-dygn, inte genom att blint gruppera den gamla motorns öppningsetiketter.

## K03. Eventordning – ett föreslaget huvudscenario

Vid gränsen T: föregående stapels close och dess riskbeslut behandlas först. Kapital vid den stängningen uppdaterar högvattenmärke. Vid UTC-midnatt sparas det föregående dygnets sista nettokapital som nytt dagsstartkapital; öppningsgap, funding och handel i nya dygnet tillhör därefter det nya dygnet.

Vid öppningen T:
1. Markera ingående q till mark_open(T). En förändring mot föregående mark_close är ett separat gapresultat, inte en ny dagsstart utan förlust.
2. Bokför funding vid T på ingående q före affärerna, till exakt avräkningsmarkpris från fryst källa. Ingen ränta fördelas jämnt över en stapel.
3. Eventuell likvidation/kapitalbrist har företräde. Sedan behandlas en enda sammanslagen avsikt i ordning: terminal stängning, permanent stopp, dagsstopp, övrig riskminskning, normal ombalansering. Risk kan aldrig skapa köp.
4. Utför och bokför affär och kostnad en gång. Spara q och E efter affären.
5. Inom nästa stapel tas inga nya beslut från high/low. Mark-extremer används för risk-/likvidationskontroll; normala beslut och drawdown-stopp utlöses vid close.

Funding före affär är en modellkonvention, inte en garanterad börsordning. Kör därför ett i förväg definierat känslighetsscenario med funding efter affär på q efter fyllning. Samma fundinghändelse får aldrig bokföras två gånger i ett scenario. Claude ska i A föreslå exakt hur klassificeringen hanterar olika beslut mellan scenarierna; ett gynnsamt scenario får inte väljas efter utfallet. Detta är en kvarstående blockerare före frysning.

Vid dagsreset återställs bara föregående dygns dagslås och räknaren för normal handel. Ett redan köat riskutträde fullföljs även om dagen har bytts. Det får inte kombineras med återinträde vid samma öppning. Nästa inträde kräver en ny tillåten normal avsikt; gamla avsikter återupplivas inte. Permanent stopp återställs aldrig.

## K04. Konto, enheter och kostnad

Använd en tydlig ledger för ett linjärt terminskontrakt, inte ett spotköp där hela köpeskillingen dras från kontot. Nettokapital = collateral inklusive realiserat resultat och alla avgifter/funding + orealiserat resultat vid markpris. Partialförsäljning realiserar bara sålda enheter; inga fiktiva fulla avslut. Kontraktspris används för affären, markpris för värdering. Visa skillnaden när priserna skiljer sig.

c = (10+2/2+5)/10 000 = 0,0016. Referenspriset för fyllning är kontraktsöppningen P. Hela c debiteras som cashkostnad på |delta_q|×P. Lägg inte samtidigt samma spread/slippage på priset så att den räknas dubbelt. Ett eventuellt effektivt pris är bara redovisning av samma kostnad.

Föreslagen mekanisk storleksregel vid tillåten fyllning: hitta q_new så att q_new×M/E_after = w, där M är aktuell mark_open, w är den redan beslutade målviktens cap, och E_after inkluderar affärens kostnad och kontraktspris–markpris-effekt. Öppningens priser får endast påverka den mekaniska exekveringsstorleken, inte signal eller beslut om band. Avvisa icke-positivt kapital och felaktiga priser; ingen klippning som döljer insolvens.

Efter fundingsteget, E=kapital före affär och q_old befintliga enheter:
- E_after = E + (q_new−q_old)×(M−P) − c×P×|q_new−q_old|.
- För vald köp/sälj-gren sätt k=M−P−cP vid köp, k=M−P+cP vid sälj.
- q_new = w×(E−q_old×k)/(M−w×k), om lösningen är ändlig, icke-negativ och konsekvent med vald gren. Annars avvisas indatan/avsikten med tydligt fel; välj inte ett negativt antal.
- Full stängning har q_new=0, kostnad cP|q_old|.

Orakel utan basisgap: E=100 000, q_old=0, P=M=100, c=0,0016, w=0,5 ger q_new=499,60031974420474, kostnad=79,93605115907276, E_after=99 920,06394884092 och vikt=0,5. Samma uppställning med w=1 får inte ge exponering över nettokapitalet på grund av avgiften.

Frys avrundningsregler/toleranser före implementation. Föreslagen forskningsmodell använder kontinuerliga enheter utan börsens lotavrundning, och märker detta som en modellbegränsning; inga dold avrundningsval får väljas efter resultatet.

## K05. Band och avsikter

Normal bandbedömning görs enbart vid dagens beslut efter close, med aktuell markvärderad q/E. |w_target−w_current| ≥ 0,02 skapar en normal avsikt, annars hold_units. En oförändrad målvikt är alltså inte automatiskt hold_units om marknadsvärdet drivit långt. Själva avsikten och dess källdata/tid ska sparas före nästa pris.

Normal avsikt fryser w, inte okänd framtida q. Enhetsberäkningen vid öppningen följer K04. Riskutträde, exakt platt signal och brott mot gällande riskcap går före bandet. Den senast kända dagliga volatilitetscapen ligger fast tills nästa kompletta dag; ingen intradagsvolatilitet införs i smyg.

Högst en normal ombalansering per UTC-dygn. Enbart 4H-öppningar är fyllningstillfällen; högst ett sammanlagt fill-event per konto/öppning. Riskreduktioner får ske utöver normalavsikten, men ett risklager får inte oscillerande skapa nya köp. Avsikter dedupliceras med konto, beslutstid och eventtyp. Fördröjningsstress måste ha en låst ersättningsregel för gamla väntande avsikter, inte en växande orderhög.

## K06. Nettorisk och intrastapelgräns

Dagsstopp: E_close/day_start−1 ≤ −0,02. Permanent stopp: E_close/close_peak−1 ≤ −0,15. Peak inkluderar 100 000 före första kostnaden. Kontroller görs efter alla kända kostnader/funding till close. Vid samtidig trigger gäller permanent stopp. Endast dagsreset får låsa upp ett dagsstopp.

Två separata riskserier krävs:
1. Faktiskt simulerade markvärderade stapelstängningar, med initialt kapital och terminal kostnad.
2. Konservativ övre gräns för intrastapel-drawdown från mark-OHLC, med explicit antagen ogynnsam ordning. Den ska benämnas en bound, inte observerad tick-drawdown.

Föreslagen bound för huvudmodellen, som inte har intrastapelorders: efter öppningens affärer/funding är q konstant inom stapeln. Beräkna E_high och E_low från samma ledger och mark_high/mark_low. Uppdatera hypotetisk peak med E_high före jämförelse med E_low. Inkludera också startkapital, alla verkliga öppnings-/stängningspunkter och avgifter. Detta är en konservativ high-före-low-ordning; behandla inte high som information till ett beslut före low. Dag-/permanent-stopp utlöses fortfarande bara av E_close, aldrig av denna diagnostiska hypotetiska peak.

För gamla jämförelser med ATR-stop kan samma q inte antas gälla hela stapeln. Claude måste före frysning skriva en eventmedveten konservativ bound som inte använder post-exit low som om positionen fortfarande fanns, men inte heller antar gynnsam stop/mark-ordning som OHLC inte visar.

Marginaltyp, maintenance tiers, likvidationsavgift, margin budget vid deländringar och historisk datakälla är ännu inte fastställda. De får inte gissas från nuvarande börsinställningar och kallas verifierade historiska regler. Det är en öppen A-blockerare att fastställa en granskningsbar modell och dess begränsningar. Ingen riktig utvärdering får passera innan riskmodellen är definierad och testbar.

## K07. Fasta jämförelser

Alla börjar med samma totalbelopp, första öppning och slutöppning enligt K02, samt samma mark-, funding- och kostnadsbokföring. Gamla publicerade H-0013-nyckeltal kopieras inte in: deras fönsterkonventioner skiljer sig. Nya kontrollkörningar ändrar inte deras gamla frysta beslut.

| Nyckel | Signal, storlek och risk |
|---|---|
| main | 7/14/28-medel, 60-dagars volcap, 2 pp band, 2 % dagsstopp och 15 % permanent stopp |
| buy_and_hold | Long 1× vid första öppningen, fasta enheter till terminal, inga strategiska dag-/DD-stopp. Likvidationsmodellen gäller ändå. |
| ema_legacy | ema_adx_trend 1.0.0 standard fast50/slow200/ADX14/min20/ATR14/stop3, allow_short=true. 4H-beslut, nästa öppning, befintlig signalutgång/fast inträdesstop, inga nya momentumriskstopp. Exakt storlekssemantik ska låsas av Claude i A. |
| bb_legacy | bb_rsi_reversion 1.0.0 standard BB20/k2/RSI14/low30/ATR14/stop2, allow_short=true; samma övergripande redovisning som ema_legacy. |
| old_mix | Hälften av kapitalet i vardera legacy-kontot från start, inga överföringar/återbalanseringar mellan kontona. Summera faktiska delkapital; motsatta positioner får inte netta bort brutto eller handelskostnader. |
| mom7, mom14, mom28 | En horisont var, annars exakt main:s volcap, band, normalhandel och riskstopp. Eget självständigt konto/riskläge. |
| no_vol | 7/14/28-medel utan volskalning, max1×, samma band och dags-/permanent-stopp som main. Ingen i efterhand uppskattad skalfaktor. |
| new_mix | En tredjedel av startkapitalet i mom7/mom14/mom28 vardera. Eget kapital, enheter och risklås per delkonto; inga kapitalöverföringar eller återställning till 1/3. Summerad ledger, inte genomsnitt av Sharpe. |

Huvudmodell väljs inte bland jämförelserna. Kontrollera särskilt skillnaden mellan summan av oberoende konton och ett gemensamt target-konto med gemensamma riskstopp.

## K08. Statistik, stresser och beslut

Hela testperiodens dagsavkastning, även platta dagar, används för Sharpe och Newey-West. Annualisering 365. Återanvänd estimatorernas befintliga formler med korrekt tidsatta avkastningar; inga tysta borttagningar av NaN på felaktig indata. Startpunkt får inte räknas som en extra avkastningsdag.

Positiv avkastning betyder strikt >0; Sharpe-jämförelser är strikt >; t-krav och drawdown-gränser är inklusive. Rapportera drawdown konsekvent som negativ avkastning och/eller positiv magnitud med explicita fältnamn. En platt kurva ger 0 avkastning, 0 t och 0 Sharpe och klarar inte kraven.

Lås N genom befintlig registerkod vid registreringen; tröskel=max(2,67,t_krav(N)). Idag finns 16 registrerade id. Inga tidigare trösklar eller resultat ändras.

Sex kriterier enligt forskningsplanen: positivt normal- och kostnadsstressnetto; t-kravet; Sharpe>buy_and_hold; Sharpe>max(ema_legacy,bb_legacy,mom7,mom14,mom28); Sharpe>old_mix och >new_mix; högst20 % close-DD och konservativ intrastapel-bound utan likvidation/riskregelbrott. Alla booleska värden måste vara korrekta JSON-booleans. MORE_RESEARCH endast när alla är sanna och körningen är giltig/fullständig.

Kostnadsstress skalar c med2,5 och räknar om hela ledgermodellen. Fundingstress dubblar positiva betalningar för long (respektive faktisk utbetalning i en kontroll med short), inte krediter. Fördröjningsstress har +4h för normala och riskavsikter, men förannonserad terminal ligger kvar vid samma slutöppning och körs där utan ytterligare fördröjning; inga order får passera slutgränsen. Känslighetsproven är fasta kontrollkörningar, inte omoptimering.

Bootstrap: föreslagen befintlig blockmetod med 20 dagars block, 2 000 resamplingar, 95 % intervall, seed0. Den är diagnostik, inte ett nytt kriterium som väljs efter utfallet.

DSR: Claude ska före registrering låsa exakt vilka run-serier/antal som redovisas, hur tidigare parametersökningar redovisas och hur beroende mellan komponenter hanteras. Antal hypotes-id, antal beräknade kontrollkurvor och antal oberoende statistiska försök är inte samma sak. Ingen hög DSR får påstås vara exakt sannolikhet för lönsamhet när beroendeantaganden inte verifierats. Detta är en öppen A-blockerare.

Spara fullständiga serier och ledger före nedsampling, inklusive partial fills, funding-event, kapital före/efter, signalens beslutstid och riskorsak. Avbrott eller datakontraktsfel sparas utan ekonomiskt godkännandebeslut. Påföljande omprov kräver att orsak och försöksidentitet redovisas.

## K09. Godkännande av leverans A

A är klar först när Claude har lämnat ett sammanhängande protokoll utan öppna metod-TODO, jämförelsematris, eventtabell och minst handräknade exempel för: första/sista dag, mark/kontraktsbasis, partial buy/sell, funding på samma gräns som handel, dagsreset med väntande riskexit, mark-high/low-ordning och skillnad mellan main och new_mix.

A1 är ett fullständigt protokollutkast med orakel, utan ny registerrad. Codex omgranskar mot denna metodgranskning och anger exakt godkänd revision. Därefter gör Claude A2 med slutligt protokoll och registreringscommit. Codex kontrollerar att A2 inte ändrat de godkända reglerna; först därefter får signalimplementation B börja. Nytt hypotes-id måste kontrolleras och registreringscommit finnas före någon historisk utvärdering; denna instruktion startar inte en sådan körning. Inga mutationer av gamla protokoll, resultat, server, SQL eller release ingår i A.
