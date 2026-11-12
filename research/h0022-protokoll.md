# H-0022: kassa-och-termin på sju altcoins med COIN-M-kvartalsterminer

Skrivet och registrerat 2026-11-12 (huvudgren `cd3190d`), **innan** någon motorkod, innan någon prisdata för strategin har hämtats eller
lästs och innan någon historisk körning. Det här dokumentet och registerraden är hela leveransen. Ingen basis, avkastning eller hållperiod har
räknats, och inget från 2025-01-01 eller senare har lästs. Protokollet ändras inte efter registreringen: en ändring är ett nytt försök med nytt id.

## Idé

En kvartalstermin handlas ofta över spotpriset, och skillnaden (basis) försvinner vid förfall. Köper man mynt på spot, lägger myntet som
säkerhet och säljer motsvarande antal kontrakt på Binance COIN-M-kvartalstermin (inversa kontrakt där vinst och förlust räknas i myntet),
är priset utjämnat och det som återstår är basis efter kostnader. Frågan är om det ger positiv avkastning över kontanter, efter realistiska
kostnader, utan att följa marknaden, på de sju altcoins som hade COIN-M-kvartal under hela perioden: ADA, BCH, BNB, DOT, LINK, LTC och XRP.

H-0020 prövade samma grundidé på BTC och ETH (USDⓈ-M, mot USDT) och fick **REJECT**. H-0022 är ett nytt försök med nytt id och räknas i N.
Skillnaderna är andra underliggande, inversa kontrakt med myntmarginal, ett förutbestämt utträde före förfall och att ingen basiströskel används.
H-0020:s trösklar (5 % in, 0 % ut, rullning vid 14 dagar) **återanvänds inte och optimeras inte**.

## Genomförbarhetsbeslut (före registreringen)

Beslut: **ett ärligt test går att låsa**. Underlag, alla redovisade i repot före detta PR:

| Krav | Läge | Belägg |
|---|---|---|
| Universum utan efterhandsurval | Biasfritt fönster med beslutsdagar 2021-03-26 till 2024-08-13; de fyra som försvann (EOS, ETC, FIL, TRX) hade sista förfall 2021-03-26 och SOL lanserades 2024-08-14 | `research/universe/coinm-pit-rapport.md`, `engine/traderlab/pit_universe.py` |
| Serier som kan väljas | `universe_at`: annonserad **och** verifierad handelsstapel beslutsdagen | PR #115 |
| Saknad annons för 0924-serien (2021) | Serien kan inte dateras och väljs inte: cykeln blir platt (se kalendern) | samma |
| Kontraktsstorlek | 10 USD, datahärledd för alla 135 serier (median 10,00) och i linje med Binance-guiden 2020 och förklaringen 2021; antagande för de sju | `research/universe/coinm-implied-contract-size.json`, `research/universe/h0022-kostnad-antaganden.md` |
| Kostnader och likvidation | Taker 0,050 %, spot 0,100 %, glidning 5 bp per ben, 50 bp per cykel (stress 125 bp); marginalkvot vid full myntmarginal oberoende av pris | PR #116, `engine/traderlab/basis_costs.py::pre_expiry_cycle` |
| Utträde utan avräkningsfönstret | Sju dagar före förfall, ingen avräkning | PR #116 |
| Data finns | Markpris per serie (månadsfiler, alla 135 serier), indexpris, spot (1d, alla sju 2021-03 till 2024-09) enligt listning av arkivet. Innehållet verifieras i datasteget (checksumma, luckor); fallerar det är körningen `OGILTIG` | listningskontroll 2026-11-12 |

Det som inte kan beläggas står under "Kända antaganden". Antalet oberoende utfall är litet (14 kvartalscykler, varav en platt), och det är
skälet till att statistiken är lagd på cykelnivå (se "Statistik").

## Regler (låsta)

| Del | Val |
|---|---|
| Instrument | Binance COIN-M-kvartalsterminer `<MYNT>USD_<ÅÅMMDD>` (1d, last price) och Binance spot `<MYNT>USDT` (1d). Mynt: ADA, BCH, BNB, DOT, LINK, LTC, XRP. BTC och ETH ingår **inte** (utesluts i förväg: inte nya underliggande, och prövade i H-0020). |
| Period | Beslutsdagar 2021-03-26 till och med 2024-06-20 (se kalendern). Första fyllning 2021-03-27, sista utträde 2024-09-20. **Inga data från 2025-01-01 eller senare läses**, och alla läsare skickar periodgränser så att arkiv från slutprovet aldrig öppnas. |
| Universum vid beslutsdagen | Serier som `universe_at` returnerar den dagen: daterad annons senast beslutsdagen, verifierad stapel med volym > 0 beslutsdagen, förfall efter beslutsdagen, inte `not_listed`, granskad data. Serier utan daterad annons (0924-serien 2021) väljs aldrig. Ingen annan serie eller dag kan ersätta en saknad. |
| Biasfritt fönster | Alla beslutsdagar ligger i `hindsight_free_window` (2021-03-26 till 2024-08-13): `hindsight_selection` är falskt varje beslutsdag. Testas. |
| Serie per cykel | Cykel k använder serien med förfall E_k enligt kalendern nedan. Ingen annan serie väljs. |
| Inträde | Villkorslöst (ingen basiströskel). Beslut vid stängning beslutsdagen, fyllning vid nästa öppning för båda benen: spot köps, terminen säljs. Ett mynt som inte är valbart är **platt** den cykeln. |
| Utträde | **Kalenderdagen sju dagar före förfallsdagen, vid öppningen 00:00 UTC** (en fredag). COIN-M-förfall sker sista fredagen 08:00 UTC, så utträdet är **176 timmar** före förfallet (inte 168, och inte dagens stängning). Terminen köps tillbaka och spoten säljs vid den dagens öppning, båda benen, med `open` i den dagens 1d-stapel. Ingen avräkning används. Reglerna är `basis_costs.exit_day`, `exit_fill_utc` och `entry_fill_utc` (tester skiljer öppning från stängning). |
| Rullning | Utträdet och nästa inträde sker vid samma öppning. Nästa serie måste vara valbar enligt beslutsdagen (dagen före), annars platt den cykeln. Cykler följer kalendern oavsett resultat. |
| Priser | Fyllning vid dagsstapelns öppning: fältet `open` i 1d-stapeln för terminsserien (last price) och för spot `<MYNT>USDT`, **samma `open_time`** för båda benen, vid inträde och utträde. Spot och termin har **separata** priser (`spot0`, `fut0`, `fut_exit`, `spot_exit`). Ingen annan stapel eller prisfält får väljas, och utträdesstapeln kan inte flyttas efter att utfallet setts. |
| Markprisdagar | Riskstoppet läser dagligt högsta markpris för **varje hållen dag från inträdesdagen till och med dagen före utträdesdagen** (`basis_costs.held_mark_days`). Utträdesdagens stapel läses inte (positionen stängs vid dess öppning). Ett stopp stängs vid nästa öppning; på sista markprisdagen är nästa öppning utträdesöppningen, men stoppet räknas ändå som utlöst. |
| Hela kapitalet och coin-marginalen (per position) | Positionens storlek `A` kommer från kassaboken nedan. Mynt köps för `A` (avgift och glidning ingår), läggs som marginal, kontrakt säljs avrundat **ned** efter öppningsavgiften (effektiv hävstång ≤ 1), PnL i mynt = n · 10 · (1/`fut_exit` − 1/`fut0`), avgifter dras i mynt, slutvärde i USD först när spot säljs. Beräknas med `basis_costs.pre_expiry_cycle`. |
| Kassabok (självfinansierande, låst) | **Startkapital 140 000 USD kontanter** vid första fyllningen (2021-03-27). Sju platser, en per mynt. Vid **varje** cykelstart har alla positioner från föregående cykel redan stängts vid samma öppning, så portföljen är ren USD-kassa `V`. Storlek per plats: `A = min(V / 7, likviditetstak)` om myntet är valbart, annars 0; är `A` under **10 000 USD** blir platsen platt. Summan av alla `A` är högst `V`, så kassan räcker alltid och ingen position kräver tillskott. Insatsen `A` lämnar kassan vid inträdet och slutvärdet (USD efter spot-sälj) kommer tillbaka vid utträdet. **Vinster återinvesteras** vid nästa cykelstart genom `V/7`; **överskott** (platta platser, platser begränsade av likviditetstaket) ligger kvar som kontanter **utan ränta** tills dess. Förluster minskar `V` och därmed nästa cykels `A`. Inga externa tillskott, inga uttag, ingen prioritering behövs (ingen brist uppstår), inget efterhandsval. Specifikationen är `basis_costs.ledger_run`. |
| Kostnader | Spot 0,100 %, termin taker 0,050 % (hela perioden, konservativt), glidning 5 bp per ben, fyra ben = **50 bp** per cykel vid noll basis. **Stress 2,5×** (alla fyra komponenter) = 125 bp (bokfört 124,2 bp: kostnaderna är andelar av ett krympande värde, så budgeten är en övre gräns inom 1 bp). Ingen BNB-rabatt, inga maker-order. |
| Markprisbaserat riskstopp | Varje hållen dag: marginalkvot (`basis_costs.margin_ratio`) vid dagens **högsta markpris** (markPriceKlines), underhållsnivå antagen **50 %**. Är kvoten ≥ **0,8** någon dag stängs båda benen vid nästa öppning (full kostnad) och myntet är platt resten av cykeln. Stoppet redovisas, och varje utlöst stopp ger **REJECT** (kriterium 5). Saknas markpris för en hållen dag är körningen `OGILTIG`. |
| Likviditetstak och minsta storlek | Positionen får vara högst **2 %** av seriens medianvolym (kassabokens tak) i USD över de senaste 20 verifierade handelsdagarna till och med beslutsdagen (volym i kontrakt × 10 USD). Färre än 20 handelsdagar eller överskriden gräns: platt. Minsta position 10 000 USD per mynt (ett kontrakt högst 0,1 %). |
| Kontraktsstorlek | Serien måste ha härledd median mellan 9,5 och 10,5 USD (`coinm-implied-contract-size.json`), annars platt (0 av 135 idag). |
| Jämförelse 1 (kontanter) | Årlig avkastning (CAGR) för **kassabokens totalvärde** `(V_slut / 140 000)^(365/1273) − 1`, över hela spannet 2021-03-27 till 2024-09-20 (1 273 dagar, inklusive platta perioder) ska överstiga **3 %**, samma gräns som i H-0020 (ungefär snittet för amerikanska 3-månadersväxlar 2021–2024; gränsen är ett förhandslåst närmevärde och inte en ny datahämtning). Annars är kontanter bättre. |
| Jämförelse 2 (marknadsneutral) | Beta mot BTCUSDT spot, regressionen på kvartalscyklernas avkastning (BTC spot, öppning till öppning, samma datum), n = 14. |
| Slumpkontroll | Inte tillämpbar (positionen är utan riktningsval). I stället redovisas *noll-basis-kostnaden* (50 bp) som referens för alla cyklers kostnad. |

## Cykelkalender (låst)

Genererad ur universumtabellen (`coinm-pit-series.json`) och `universe_at`; inga priser används. Cykel 2 är platt för alla mynt eftersom 0924-serien
2021 saknar daterad annons (kunde inte dateras, därför väljs den aldrig). Cykel 1 är kortare (83 dagar). Sista beslutsdag är 2024-06-20.

| Cykel | Serie (förfall) | Beslutsdag (stängning) | Inträde (fyllning vid öppning 00:00 UTC) | Utträde (fyllning vid öppning 00:00 UTC, kalenderdag förfall − 7) | Valbara underliggande vid beslutsdagen | Dagar |
|---|---|---|---|---|---|---|
| 1 | 2021-06-25 | 2021-03-26 | 2021-03-27 | 2021-06-18 | alla sju | 83 |
| 2 | 2021-09-24 | 2021-06-17 | 2021-06-18 | 2021-09-17 | **ingen (serien saknar daterad annons): platt** | 91 |
| 3 | 2021-12-31 | 2021-09-16 | 2021-09-17 | 2021-12-24 | alla sju | 98 |
| 4 | 2022-03-25 | 2021-12-23 | 2021-12-24 | 2022-03-18 | alla sju | 84 |
| 5 | 2022-06-24 | 2022-03-17 | 2022-03-18 | 2022-06-17 | alla sju | 91 |
| 6 | 2022-09-30 | 2022-06-16 | 2022-06-17 | 2022-09-23 | alla sju | 98 |
| 7 | 2022-12-30 | 2022-09-22 | 2022-09-23 | 2022-12-23 | alla sju | 91 |
| 8 | 2023-03-31 | 2022-12-22 | 2022-12-23 | 2023-03-24 | alla sju | 91 |
| 9 | 2023-06-30 | 2023-03-23 | 2023-03-24 | 2023-06-23 | alla sju | 91 |
| 10 | 2023-09-29 | 2023-06-22 | 2023-06-23 | 2023-09-22 | alla sju | 91 |
| 11 | 2023-12-29 | 2023-09-21 | 2023-09-22 | 2023-12-22 | alla sju | 91 |
| 12 | 2024-03-29 | 2023-12-21 | 2023-12-22 | 2024-03-22 | alla sju | 91 |
| 13 | 2024-06-28 | 2024-03-21 | 2024-03-22 | 2024-06-21 | alla sju | 91 |
| 14 | 2024-09-27 | 2024-06-20 | 2024-06-21 | 2024-09-20 | alla sju | 91 |

Antal cykler **n = 14** (13 med positioner, 1 platt). Hela spannet är 1 273 dagar (3,49 år).

## Kassaboken: två syntetiska cykler räknade för hand

Alla siffror nedan är syntetiska och reproduceras exakt av `ledger_run` (test `test_ledger_exempel_vinst_och_forlust_tva_cykler`). Kostnader: spot 0,100 %, termin taker 0,050 %, glidning 5 bp per ben. Kontraktsstorlek 10 USD.

**Cykel 1.** Start `V = 140 000`. Sju valbara platser, alla utan tak, så `A = V/7 = 20 000` per plats. Sex platser: spot0 100, fut0 104, fut_exit 100,5, spot_exit 100 (basis 4 % → 0,5 %). Sjunde platsen: spot0 100, fut0 100, fut_exit 103, spot_exit 100 (basis vidgas, förlust).

| Plats | A (USD) | Kontrakt | Slutvärde (USD) | Avkastning |
|---|---|---|---|---|
| 1 till 6 (varje) | 20 000,00 | 2 074 | 20 593,04 | +2,9652 % |
| 7 | 20 000,00 | 1 995 | 19 320,63 | −3,3968 % |

Investerat 140 000,00, kassa 0, `V_slut` = 6 × 20 593,04 + 19 320,63 = **142 878,86** (avrundat till cent), r₁ = **+2,0563 %**.

**Cykel 2.** Start `V = 142 878,86`, `V/7 = 20 411,27`. Plats 1 är inte valbar (platt). Plats 2 har likviditetstak 15 000 (`A = min(20 411,27; 15 000) = 15 000`). Platserna 3 till 6 vinner (som ovan), plats 7 har fut0 100 och fut_exit 104 (förlust).

| Plats | A (USD) | Kontrakt | Slutvärde (USD) | Avkastning |
|---|---|---|---|---|
| 1 | 0 (platt) | 0 | 0 | 0 |
| 2 | 15 000,00 | 1 556 | 15 444,94 | +2,9662 % |
| 3 till 6 (varje) | 20 411,27 | 2 117 | 21 016,61 | +2,9657 % |
| 7 | 20 411,27 | 2 036 | 19 528,34 | −4,3257 % |

Investerat 117 056,33, kassa som står kvar 25 822,53, `V_slut` = 25 822,53 + 15 444,94 + 4 × 21 016,61 + 19 528,34 = **144 862,25**, r₂ = **+1,3882 %**. Totalt +3,4730 % över två cykler.

Kontroller som motorn måste uppfylla: summan av `A` är aldrig större än `V`; `V_slut = V_start − Σ A + Σ slutvärde`; nästa cykels `V_start` är föregående `V_slut`; CAGR, t och beta beräknas ur samma `V`-serie. Stress (2,5×) körs som en **egen** kassabok med stressade kostnader från samma startkapital, där varje cykels `V` kommer ur den bokens egen utveckling.

## Statistik: 14 starkt korrelerade kvartalscykler

Positionerna för de sju mynten rör sig ihop (samma börs, samma regim, samma kalender), och cyklerna är kvartal. Dagsavkastningen i en säkrad kassa-och-termin
är nästan en jämn upplupen basis, så ett dagligt t-värde vore kraftigt överskattat jämfört med de **14** oberoende utfallen. Därför är beslutsstatistiken lagd på cykelnivå:

* En observation per cykel, **ur kassaboken**: r_k = V_slut / V_start − 1 för cykel k (hela portföljen, platta platser och kontanter ger 0 för sin del, den platta cykeln 2 ger exakt 0). Samma r_k används för t, beta och CAGR.
* t = medelvärde(r_k) / (std(r_k) / √14), med n−1 = 13 frihetsgrader.
* Kravet är **max(2,84; Student-t-kvantilen med 13 frihetsgrader för p = 0,05/22)** = max(2,84; **3,42**) = **3,42**. 2,84 är Bonferronikravet för N = 22 (`python -m traderlab krav 22`);
  3,42 är det strängare kravet för så få observationer. Båda är bestämda nu.
* Redovisas utan att styra beslutet: bootstrap-intervall för medelavkastningen (cyklerna omsamplas, 10 000 dragningar, fast frö 0), antal positiva cykler, per mynt och per år, in- och utträdesbasis,
  och ett dagligt Newey-West-t som är **uttryckligen inte beslutsgrundande** (överskattar signifikansen här).
* Beta mot BTC beräknas på samma 14 cykler och redovisas med konfidensintervall; kriteriet nedan använder punktskattningen.

Ett positivt resultat med så få oberoende utfall är svagt bevis även om kriterierna klaras: det betyder bara att idén får granskas och prövas på den orörda perioden och på papper.

## Beslutskriterier (spår C, bestämda nu)

`MORE_RESEARCH` om **alla** gäller, annars `REJECT`:

1. t över de 14 cyklerna ≥ **3,42** (se ovan; N = 22, Bonferronikrav 2,84, skärpt till t-kvantilen för 13 frihetsgrader).
2. Avkastning med **2,5 gånger** kostnaderna > 0 (sammanvägd över alla cykler).
3. |beta mot BTCUSDT spot| ≤ **0,2** (cykelregressionen).
4. Årlig avkastning (CAGR) över hela spannet, inklusive platta perioder, > **3 %**.
5. **Inget riskstopp utlöst** (marginalkvot aldrig ≥ 0,8) och ingen likvidation.

Godkänt betyder bara att idén får granskas och sedan testas på slutprovet (2025-01 till 2026-09) och på papper. Det betyder inte att strategin tjänar pengar framåt.

## Datakrav (annars `OGILTIG`, inget beslut, aldrig `MORE_RESEARCH`)

1. Verifierade dagsstaplar (checksumma, SHA-256 mot manifest där luckor fyllts, grannkontroll enligt `gapcheck.combined`) för terminsserien och spoten på varje inträdes- och utträdesdag för varje position.
2. Markpris (daglig high) för terminsserien varje hållen dag.
3. En saknad stapel på **utträdesdagen** (terminen eller spoten) för en hållen position: `OGILTIG`. En saknad stapel på beslutsdagen gör bara myntet platt den cykeln.
4. Minst **46** av 91 möjliga mynt-cykler (7 × 13) handlade, och minst **10** av de 13 cyklerna med minst **4** handlade mynt. Annars för få observationer: `OGILTIG`.
5. Inga arkiv från 2025-01-01 eller senare har öppnats (test).
6. Universumtabellen är den som ligger på huvudgrenen vid registreringen (`research/universe/coinm-pit-series.json`) och cykelkalendern ovan reproduceras exakt (test).
7. Luckor fylls aldrig med sista kända värde eller ersättare. En ogiltig körning redovisas som en ny rad och försöket räknas.

## Kända antaganden och svagheter (skrivna i förväg)

* **H-0020 är REJECT** på BTC och ETH, samma börs och delvis samma period (2021–2024). Resultatet här förväntas vara korrelerat med det. Priserna för dessa mynt är också sedda i H-0014 till H-0021 (USDT-terminer). Det är därför ett nytt försök med högre krav, inte en oberoende bekräftelse.
* **Få och korrelerade utfall:** 14 kvartalscykler. Ett REJECT eller `MORE_RESEARCH` med låg styrka är det troliga. Cykelkalendern ger regimer (2021 uppgång, 2022 nedgång, 2023–24 återhämtning) som kan avgöra resultatet.
* **Likviditet:** nästa serie vid utträdet är i regel den näst närmaste, som kan vara tunnare än närmaste serien. Likviditetstaket gör sådana mynt-cykler platta, vilket kan minska antalet observationer (datakrav 4).
* **Spread och glidning är ett antagande** (5 bp per ben), inte en mätning. Stresstestet 2,5× ska visa om slutsatsen vänder.
* **Kontraktsstorlek 10 USD** är datahärledd, inte en Binance-källa per kontrakt. Marginalnivån (50 %) och stoppet 0,8 är antaganden: underhållsnivåerna höjdes stegvis 2021-02 till 2021-05 och stegen är inte arkiverade.
* **Avgifter:** taker 0,050 % hela perioden och spot 0,100 % utan rabatt är konservativa; verkliga nivåer kan ha varit lägre (0,040 % före 2021-04-27, BNB-rabatt).
* **Utträdet 176 timmar före förfall (öppningen sju kalenderdagar före förfallsdagen)** innebär en basisrest som inte har konvergerat. Den ingår i utfallet. Avräkningsfönstrets motsägelse (timmesmedel mot 30 minuter) undviks.
* **Motpartsrisk och exekvering** finns inte i ett backtest: börsfallissemang (FTX 2022), uttagsstopp, ADL, två order som inte fylls exakt samtidigt, och att Binance kan ha ändrat regler.
* **Kapital utan ränta:** platta mynt och kontanter ger 0 %, vilket är konservativt men inte realistiskt. Kontantgränsen 3 % är ett närmevärde.
* **Perioden är rent hindsight-fri för universumet** men inte för kunskapen om att basis på dessa kontrakt redan setts i H-0020 på BTC/ETH.

## Före körning

Motorkoden skrivs i en **separat PR** och granskas innan något körs. Den ska återanvända `pit_universe.universe_at`, `basis_costs.pre_expiry_cycle` och `margin_ratio`, `gapcheck.combined`
och läsare med periodgränser, och ha tester för:

1. look-ahead (beslut använder bara data till och med beslutsdagen) och slutprovsskyddet (ingen fil från 2025 eller senare öppnas),
2. att cykelkalendern ovan reproduceras exakt, inklusive den platta cykeln 2,
3. att serier utan daterad annons, utan verifierad stapel beslutsdagen, med luckor eller över likviditetsgränsen blir platta och aldrig ersätts,
4. att augustiluckan 2023 fylls bara med verifierade dagsstaplar och märks i proveniensen,
5. separata spot- och terminspriser vid in- och utträde, och att `pre_expiry_cycle` (inte avräkning) används,
6. riskstoppets definition (marginalkvot ≥ 0,8 på dagens högsta markpris stänger vid nästa öppning, ett stopp ger REJECT),
7. kostnadsbudgeten 50 bp (125 bp i stress) vid noll basis och att en saknad utträdesstapel ger `OGILTIG`.

Datahämtning för strategin (markpris, spot) görs först i den PR:en och först efter att den här registreringen är granskad och mergad.

## Källor

`research/universe/coinm-pit-rapport.md`, `research/universe/coinm-pit-series.json`, `research/universe/h0022-kostnad-antaganden.md`, `research/universe/coinm-implied-contract-size.json`,
`research/h0022-forutsattningar.md`, `research/cm-lucka-2023-08.md`, `engine/traderlab/pit_universe.py`, `engine/traderlab/basis_costs.py`, `engine/traderlab/data/gapcheck.py`,
Binance-meddelanden i `research/coverage/basis-sources-ann1-*.json`, `…pit1-*.json`, `…cost1-*.json` och `…cost2-*.json`.
