# H-0017 C6-01 – Codex granskning av beslutsunderlaget

Datum: 2026-11-04. **Bedömning: BEHÖVER RÄTTAS före Edwins beslut.** Inget alternativ väljs och ingen rekommendation grundas på resultat.

Granskad revision: `96969f4c49fdfc8d736e0da2a19b6a2a47858b12`, gren `codex/momentum-c6-review`. HEAD och gren kontrollerades lokalt; `git status --short` var tom före arbetet. Granskningsobjekt: [beslutsunderlaget](momentum-C6-01-beslutsunderlag.md). Styrande källor: [frysta protokollet](../research/h0017-protokoll.md), §8.3, §9, §10.1–10.2, §13 och D21; [Edwins C5-01-beslut](momentum-C5-01-edwins-beslut.md); [ordningsbeslutet](momentum-C5-01-ordningsbeslut.md); [C6-uppdraget, C6-01](claude-uppdrag-momentum-C6.md#materiell-öppen-fråga-c6-01--till-codex-och-edwin-före-berörd-kodning).

Detta är en dokumentgranskning, inte ett implementationsgodkännande. Endast denna nya fil ändras. Status, genererade checklistor, underlag, kod, protokoll och audits lämnas orörda enligt den uttryckliga avgränsningen. Ingen commit eller historikkörning görs. H-0013 förblir REJECT.

## Oberoende Decimalverifiering

Omräkning utförd med Python 3, `decimal.Decimal` från strängar, precision 60; inga produktionsfunktioner eller floatvärden användes. Formler: p=q×M_ref×ränta, E=C+q×M, MM=mmr×|q|×M och d=E/max(tidigare peak,E)−1 i punktordning. Följande är lokala syntetiska konsekvensberäkningar, inte en verifierad nåbar main-körning från startkontot.

- Föregående close: −600 000+10 000×70=100 000.
- Betalning: 10 000×64×0,02=12 800; kredit: −12 800. Summan är 0.
- C_high=−587 200; C_low=−612 800; E_open=E_trade=E_post=40 000 i de två intrastapelfallen. Gapmarginalen är 32 000 vid mmr=0,05: 40 000>32 000, alltså ingen öppningsträff där.

| Fall | E_high | E_low i marginalunderlaget | MM 0,05 | MM 0,005 | Slutsats |
|---|---:|---:|---:|---:|---|
| 1, low 63,5 | 72 800 | 22 200 | 31 750 | 3 175 | Träff vid 0,05; ingen träff vid 0,005 |
| 2, low 58 | 72 800 | −32 800 | 29 000 | 2 900 | Träff vid båda satserna |
| 3, gap 55 | Ej tillämpligt | E_gap=−50 000 | 27 500 | 2 750 | Gapträff vid båda satserna |

Fall 3 måste läsas som ett separat gapfall. Om mellanevent alls anges där är deras M_ref=55 och kategorin efter känd gaplikvidation absorberad; beloppen ±12 800 från O=64 hör inte till detta fall. Inga extrema punkter med gammal position får följa gapträffen.

Med ingående boundpeak 101 000 blir punktvisa drawdowns:

| E | Exakt kvot | Decimal (avrundad här) |
|---|---|---:|
| 40 000 | −61/101 | −0,603960396039603960 |
| 72 800 | −141/505 | −0,279207920792079208 |
| 22 200 | −394/505 | −0,780198019801980198 |
| −32 800 | −669/505 | −1,324752475247524752 |
| −50 000 | −151/101 | −1,495049504950495050 |
| 0 | −1 | −1 |

A:s sekvenser är således [40 000,40 000,40 000,72 800,22 200,0], [40 000,40 000,40 000,72 800,−32 800,0] respektive [−50 000,0]. Peak är 101 000 i samtliga, trough är 0, −32 800 respektive −50 000. Underlagets tre A-värden och deras avrundningar stämmer. B och C ger trough 0 och lokal minsta drawdown −1 i alla tre fallen enligt de föreslagna nollkonventionerna. Ingen division med noll sker; peak behålls från minst 100 000.

Vid mmr=0,005 utan träff i fall 1 bokförs båda mellaneventen: C_close=−600 000, E_close=50 000. High/low och löpande peak är oförändrade; lokal minsta drawdown är då −394/505≈−0,780198019801980198. Vid träff är faktisk close och terminal däremot 0, inte −600 000+q×mark_close. Båda OHLC-tabellerna är giltiga som prisuppgifter.

**Historikförbehåll:** En ingående peak bestämmer inte tidigare minsta drawdown. Tabellen kan kallas hela förloppets `max_dd_bound` endast om tidigare ackumulerat minimum inte redan är lägre. Annars gäller min(tidigare minimum, lokalt minimum). Underlaget behöver ange detta antagande eller kalla värdena lokala bidrag. Samma förbehåll gäller påståendet att B/C alltid ger exakt magnitud 1: en redan tidigare negativ hypotetisk punkt kan ha gett större magnitud.

## Hänvisningar och alternativens neutralitet

Hänvisningarna till §9, §13.2 och D21 är sakligt riktiga. C5-01 återges korrekt: öppningens bokföring står kvar, ingen mellanfunding bokförs i träffstapeln, marginalunderlaget bevaras och de olösta beloppen redovisas separat. Detta tillåter inte att hypotetisk funding bokförs eller att träffens tid uppfinns. §10.2:s citerade ordning och fundingbas är korrekta för dess angivna konstanta q; kapitlet specificerar inte uttryckligen fortsättningen vid likvidation.

1. **A är ett förslag till tillägg, inte entydigt ”§10.2 som skrivet fram till nollpunkten” (rad 51).** Den rubriken ger A ett obestyrkt försteg. §9/D21 säger noll efter träff men låser inte vilka hypotetiska punkter som ska föregå nollan. Beskriv A neutralt som high/low med olöst hypotetisk funding och oklippta negativa värden. Underlagets rad 30–31 bör säga att talen sammanfaller *om denna low-konvention väljs*. Marginalprövningen är oberoende av om bounden har en sådan punkt. Den är inte en observerad träfftid vid low.
2. **B är inte ett färdigt punktkontrakt.** ”Ingen punkt under 0” kan betyda att negativa punkter utelämnas eller att de ersätts med 0. Samma minimum i exemplen gör inte punktsekvenserna lika. C6-uppdraget förbjuder tyst klippning. Ett uttryckligt valt tillägg måste ange mekanismen, fas/proveniens och bevara det råa negativa värdet separat. B/C:s gapsekvens måste därför skrivas ut.
3. **C kopplar ihop oberoende val.** Att utelämna high/low vid okänd intrastapelträff kräver inte att ett känt negativt gapvärde också utelämnas. Varianten ”inga high/low vid intrastapelträff, men oklippt gap före noll” saknas. Den skulle ge −1 i fall 1/2 och −151/101 i fall 3 (med historikförbehållet ovan).
4. **Ett relevant fundingalternativ saknas:** behåll hypotetiska high/low med q_open men använd C_post utan olöst mellanfunding. Då blir high 60 000, low 35 000 respektive −20 000. Marginalunderlaget är fortfarande 22 200 respektive −32 800 och träffflaggan ändras inte. Med oklippta värden och nollpunkt blir lokala minimum −1 respektive −121/101≈−1,198019801980198020. Gapregeln kan väljas separat. Detta är också ett materiellt tillägg till §10.2:s fundingregel, inte en redan godkänd eller rekommenderad lösning. Att behålla extremer och att använda olösta fundingbelopp är två olika frågor.
5. **Negativt kapital kräver en konservativitetsreservation.** §10.2 motiverar high-före-low med positivt kapital. För negativ trough är derivatan av E/peak−1 med avseende på peak positiv: en högre peak gör drawdown mindre negativ. Exempel: −32 800/101 000−1=−669/505, medan −32 800/120 000−1=−191/150≈−1,273333333333333333. Underlagets påstående att högre peak kan ändra A:s negativa fall stämmer, men riktningen och begränsningen saknas. A får inte marknadsföras som bevisat strängaste bound under −100 %. Även peak och punktspår kan skilja mellan alternativen trots samma slutliga minimum.

Exemplen räcker för de angivna talen men visar ingen ny hypotetisk peak. Ett kompletterat konsekvensunderlag behöver visa även en high som höjer peak och en tidigare negativ boundpunkt, så att konsekvenserna för ackumulerat mått och påstådd konservativitet framgår. Detta kräver inga marknadsdata eller resultatval.

## C6 och beslutseffekt

**Ja: valet av dessa rena boundkonventioner kan inte rädda C6 vid likvidation i main.** För en i övrigt giltig körning är C6 falskt genom ”ingen likvidation i main” i §13.2, oberoende av boundvärdet. Dessutom ger den absorberande nollan minst 100 % drawdown i både close- och boundserien med bevarad positiv peak. 20 %-gränsen är därmed passerad även med en konvention som utesluter negativa värden. I träfffria main-förlopp ska C6-01 inte ändra något. I gridet räcker ett scenario som underkänns för att MORE_RESEARCH inte ska kunna ges.

Rad 73:s ”REJECT/PASS eller något beslut” ska begränsas. Protokollets namn är REJECT/MORE_RESEARCH; PASS är inget slutbeslut. Slutsatsen gäller ekonomisk klassificering av giltig körning med oförändrad ledger, marginalflagga, close-serie och träfffria fall. OGILTIG/OGILTIG_DATA är separata från ekonomiskt REJECT (§13.3). Kontraktsvalet påverkar fortfarande redovisning och vad som får implementeras/godkännas. Samma ekonomiska utfall ersätter inte Edwins beslut. Övriga kontons bound är diagnostik, men denna granskning fastställer ingen generell boundkonvention för legacy-short, ATR-stop eller blandningar.

## Exakta frågor till Edwin

Underlagets fråga 1 blandar fundingbas och existens av extremer; fråga 2 döljer att gap kan behandlas separat; fråga 3 är ett påstående i stället för ett val. Ersätt med följande valfrågor. Inget svar är förvalt. Ett fullständigt svar kan anges som exempelvis `1=…, 2=…, 3=…, 4=…` utan fri tolkning av A/B/C.

**1. Vilka hypotetiska extrempunkter ska ingå vid intrastapelträff i huvudmodellens §10.2-bound? Välj ett:**

- **H1:** high och low med q_open och C_high=C_post−Σmin(p_i,0), C_low=C_post−Σmax(p_i,0), där alla olösta mellanevent används enbart hypotetiskt.
- **H2:** high och low med q_open och samma C_post för båda, utan olösta mellanevent i bounden. Marginalprövningen använder fortfarande sitt oförändrade fundingunderlag.
- **H3:** inga high/low i träffstapeln; öppningsfaserna följs av likvidationsnollan.

**2. Hur ska negativa råvärden i intrastapelträffstapelns valda boundpunkter före reset behandlas? Välj ett:**

- **I1:** behåll dem oklippta som signerade boundpunkter, även under −100 % drawdown.
- **I2:** utelämna negativa punkter ur boundserien; behåll råvärde och orsak i separat spår. Likvidationsnollan ingår alltid.
- **I3:** ersätt negativa boundpunkters E med 0 genom en uttrycklig boundkonvention; behåll råvärde och omvandling i spåret. Faktisk ledger och marginalunderlag ändras inte.

Frågan omfattar alla valda kapitalfaser som kan vara negativa; inte bara E_low. Med H3 omfattar den kvarvarande öppningsfaser. Ingen sådan regel gäller ett oförklarat negativt levande konto utanför dokumenterad träff.

**3. Hur ska ett negativt gap-/öppningsprövningsvärde före känd öppningslikvidation behandlas i bounden? Välj ett, oberoende av fråga 1–2:**

- **G1:** inkludera det råa negativa värdet före likvidationsnollan.
- **G2:** utelämna det negativa värdet ur boundserien men behåll det i gap-/marginalspåret; inkludera likvidationsnollan.
- **G3:** inkludera en uttryckligen till 0 omvandlad boundpunkt före likvidationsnollan, med råvärdet och omvandlingen i spåret.

Gap och eventuell A-funding/prövningsfas bevarar C5:s faktiska ordning och proveniens; inga trade/post/high/low med position skapas efter känd öppningslikvidation.

**4. Godkänner du följande fullständiga placerings- och dokumentationsregel? Välj ett:**

- **P1 – Godkänn:** vid intrastapelträff kommer likvidationsnollan efter den valda hypotetiska low-fasen (H1/H2), eller efter sista tillåtna öppningsfas (H3). Vid öppningsträff kommer den efter C5:s gap/A-/prövningssteg som faktiskt hunnit ske, med negativa punkter enligt G-valet. Faktisk close och terminal är 0. Peak och tidigare drawdownminimum behålls. Därefter endast absorberande noll, inga gamla positionsextremer, affärer eller funding. Hypotetisk punktordning är ingen påstådd tidsordning mellan träff, extremer och funding. Alla mellanevent vid intrastapelträff förblir olösta i ledgern enligt C5-01. Valen dokumenteras som separat länkat C6-01-tillägg, med reservation om konservativitet för negativt kapital; frysta protokollet och C5-01 skrivs inte om. Omfattningen är huvudmodell long/platt inom C6-uppdraget, inte ett legacybeslut.
- **P2 – Återremittera:** ingen semantik godkänns för implementation; ett nytt preciserat placerings-/dokumentationsförslag krävs före beslut.

Dessa frågor låser redovisningskontraktet; de frågar inte vilket alternativ som ger önskat resultat. Efter ett dokumenterat beslut krävs Codex granskning av svaret och därefter separat implementation och syntetisk verifiering. C6/MOM-C04 är inte godkänt genom denna granskning.
