# H-0023: kassa-och-termin på sju altcoins med Rullning B (inträde i närmaste serie efter föregående förfall)

Skrivet och registrerat 2026-11-12 (huvudgren `e78dd7e`), **innan** någon motorkod, innan någon prisdata för strategin har hämtats eller lästs och innan någon
historisk körning. Det här dokumentet och registerraden är hela leveransen. Ingen basis, avkastning, t-statistik eller beta har räknats, och inget från
2025-01-01 eller senare har lästs. Protokollet ändras inte efter registreringen: en ändring är ett nytt försök med nytt id.

## Idé

Samma grundidé som H-0022: köp mynt på spot, lägg myntet som säkerhet och sälj motsvarande heltalskontrakt på Binance COIN-M-kvartalstermin (inversa kontrakt med
myntmarginal), så att priset utjämnas och det som återstår är basis efter kostnader. Frågan är om det ger positiv avkastning över kontanter efter realistiska kostnader,
utan att följa marknaden, på ADA, BCH, BNB, DOT, LINK, LTC och XRP.

**Den enda strategiska skillnaden mot H-0022 är tidtabellen ("Rullning B"), låst i `research/rullning-b-kandidat.md` (commit `3be2903`) före all volymmätning:** i stället för att gå in i den
näst närmaste serien redan vid föregående utträde (sju dagar före förfall) går man in **efter föregående kontrakts förfall** i den då närmaste kvartalsserien, med beslut på
förfallsdagens avslutade dagsstapel och fyllning vid nästa 00:00 UTC. Utträdet är oförändrat: 00:00 UTC sju kalenderdagar före serien förfall. Portföljen ligger i kontanter utan ränta
under de åtta dagarna däremellan.

## Läget före registreringen (öppen redovisning)

* **H-0020 är `REJECT`** (BTC och ETH, USDⓈ-M, samma börs och delvis samma period). H-0023 är ett nytt försök med nytt id och räknas i N (N = 23).
* **H-0022 är `OGILTIG` utan körning:** datatäckningsgranskningen (PR #119, `research/universe/h0022-datatackning.md`) visade att högst 9 av 13 cykler kunde ha minst fyra handlade
  mynt, medan datakravet var 10, eftersom den inrullade, näst närmaste serien var för tunn. Registret säger det (PR #120). Ingen strategiavkastning har räknats för H-0022.
* **Kalendern valdes efter H-0022:s volymdiagnos.** Det är en designfrihet: Rullning B formades av att den föregående tidtabellen föll på volym (volym, inte avkastning). Exakt en tidtabell har prövats
  (PR #121), och ingen parameter har valts utifrån avkastning, för ingen avkastning har räknats.
* **Täckningen når 10 av 13 cykler bara i bästa fall, utan marginal** (PR #121, `research/universe/rullning-b-rapport.md`): 63 av 91 mynt-cykler och exakt 10 cykler med minst fyra mynt vid minsta position, och det
  beror på en enda cykel (cykel 10, 3 → 4 mynt). Det är en övre gräns, inte ett godkänt strategitest. **En faktisk körning kan därför fortfarande bli `OGILTIG`** (datakrav 4), och kassabokens värde kan göra det
  sannolikare.
* Alla 91 möjliga mynt-cykler har kompletta, verifierade data (1 463 filer, 0 checksummefel). Markprisluckan 2023-08 täcks av verifierade dagsfiler (manifest i repot).

Beslut: **ett ärligt, men knappt genomförbart, test går att låsa.** Ingen ny oöverstiglig datagräns har hittats.

## Regler (låsta, samma som H-0022 utom tidtabellen)

| Del | Val |
|---|---|
| Instrument | Binance COIN-M-kvartalsterminer `<MYNT>USD_<ÅÅMMDD>` (1d, last price) och Binance spot `<MYNT>USDT` (1d). Mynt: ADA, BCH, BNB, DOT, LINK, LTC, XRP. BTC och ETH ingår **inte** (utesluts i förväg: inte nya underliggande, och prövade i H-0020). |
| Period | Beslutsdagar 2021-03-26 till och med 2024-06-28 (se kalendern). Första fyllning 2021-03-27, sista utträde 2024-09-20 (samma spann på 1 273 dagar som H-0022). **Inga data från 2025-01-01 eller senare läses**, och alla läsare skickar periodgränser så att arkiv från slutprovet aldrig öppnas. |
| Universum vid beslutsdagen | Serier som `universe_at` returnerar den dagen: daterad annons senast beslutsdagen, verifierad stapel med volym > 0 beslutsdagen, förfall efter beslutsdagen, inte `not_listed`, granskad data. Serier utan daterad annons (0924-serien 2021) väljs aldrig. Ingen annan serie eller dag kan ersätta en saknad. |
| Biasfritt fönster | Alla beslutsdagar ligger i `hindsight_free_window` (2021-03-26 till 2024-08-13): `hindsight_selection` är falskt varje beslutsdag. Testas. |
| Serie per cykel | Cykel k använder den kvartalsserie vars förfall `E_k` är **närmast efter föregående kontrakts förfall** `E_{k-1}` (efter `E_{k-1}` är det den närmaste serien). Är den inte valbar på beslutsdagen blir myntet platt den cykeln. **Ingen annan serie ersätter den** (inte heller nästa serie efter `E_k`). |
| Inträde | Villkorslöst (ingen basiströskel). **Beslutsdag `D_k` = föregående förfallsdag `E_{k-1}`** (en fredag; förfall 08:00 UTC). Beslutet fattas på den dagens **sista avslutade dagsstapel** (stapeln för `E_{k-1}`, färdig vid 00:00 UTC dagen efter) och fyllningen sker vid **nästa 00:00 UTC**, `F_k = D_k + 1 dag` (lördag), `open` i den dagens 1d-stapel för båda benen: spot köps, terminen säljs. Ett mynt som inte är valbart är **platt** den cykeln. Första cykeln: `D_1 = 2021-03-26`, `F_1 = 2021-03-27`. Reglerna är `basis_costs.entry_fill_utc` och `roll_decision_day`. |
| Utträde | **Kalenderdagen sju dagar före förfallsdagen, vid öppningen 00:00 UTC** (en fredag). COIN-M-förfall sker sista fredagen 08:00 UTC, så utträdet är **176 timmar** före förfallet (inte 168, och inte dagens stängning). Terminen köps tillbaka och spoten säljs vid den dagens öppning, båda benen, med `open` i den dagens 1d-stapel. Ingen avräkning används. Reglerna är `basis_costs.exit_day`, `exit_fill_utc` och `entry_fill_utc` (tester skiljer öppning från stängning). |
| Rullning | **Utträdet (sju dagar före förfall) och nästa inträde sker inte vid samma öppning:** portföljen ligger i **kontanter utan ränta** från utträdet vid `X_{k-1}` till inträdet vid `F_k` (åtta dagar). **Valet av serie fattas på beslutsdagen `D_k`, dagen före fyllningen** (stängning), och använder bara data till och med den dagen: annons, verifierad handelsstapel med volym, 20-dagars medianvolym, kontraktsstorlekskontroll och spot. Utträdesdagens egen stapel (fyllningsdagen) är inte färdig vid 00:00 och används **aldrig** för valet, och ett senare utfall, en saknad stapel eller nollvolym den dagen ändrar inte beslutet (`basis_costs.select_for_fill`, `liquidity_cap_usd`). Är serien inte valbar på beslutsdagen blir myntet platt den cykeln. Cykler följer kalendern oavsett resultat. |
| Priser | Fyllning vid dagsstapelns öppning: fältet `open` i 1d-stapeln för terminsserien (last price) och för spot `<MYNT>USDT`, **samma `open_time`** för båda benen, vid inträde och utträde. Spot och termin har **separata** priser (`spot0`, `fut0`, `fut_exit`, `spot_exit`). Ingen annan stapel eller prisfält får väljas, och utträdesstapeln kan inte flyttas efter att utfallet setts. |
| Markprisdagar | Riskstoppet läser dagligt högsta markpris för **varje hållen dag från inträdesdagen till och med dagen före utträdesdagen** (`basis_costs.held_mark_days`). Utträdesdagens stapel läses inte (positionen stängs vid dess öppning). Ett stopp stängs vid nästa öppning; på sista markprisdagen är nästa öppning utträdesöppningen, men stoppet räknas ändå som utlöst. |
| Hela kapitalet och coin-marginalen (per position) | Positionens storlek `A` kommer från kassaboken nedan (oförändrad från H-0022). Mynt köps för `A` (avgift och glidning ingår), läggs som marginal, kontrakt säljs avrundat **ned** efter öppningsavgiften (effektiv hävstång ≤ 1), PnL i mynt = n · 10 · (1/`fut_exit` − 1/`fut0`), avgifter dras i mynt, slutvärde i USD först när spot säljs. Beräknas med `basis_costs.pre_expiry_cycle`. |
| Kassabok (självfinansierande, låst) | **Startkapital 140 000 USD kontanter** vid första fyllningen (2021-03-27). Sju platser, en per mynt. Vid **varje** cykelstart (inträdet `F_k`) har alla positioner från föregående cykel redan stängts vid `X_{k-1}`, åtta dagar tidigare, så portföljen är ren USD-kassa `V` (kontanter utan ränta under väntan). Storlek per plats: `A = min(V / 7, likviditetstak)` om myntet är valbart, annars 0; är `A` under **10 000 USD** blir platsen platt. Summan av alla `A` är högst `V`, så kassan räcker alltid och ingen position kräver tillskott. Insatsen `A` lämnar kassan vid inträdet och slutvärdet (USD efter spot-sälj) kommer tillbaka vid utträdet. **Vinster återinvesteras** vid nästa cykelstart genom `V/7`; **överskott** (platta platser, platser begränsade av likviditetstaket) ligger kvar som kontanter **utan ränta** tills dess. Förluster minskar `V` och därmed nästa cykels `A`. Inga externa tillskott, inga uttag, ingen prioritering behövs (ingen brist uppstår), inget efterhandsval. Cykelavkastningen `r_k = V_slut / V_start − 1` mäts från `F_k` till `F_{k+1}` (kontanterna är oförändrade under de åtta dagarna, så det är samma värde som direkt efter utträdet). Specifikationen är `basis_costs.ledger_run`. |
| Kostnader | Spot 0,100 %, termin taker 0,050 % (hela perioden, konservativt), glidning 5 bp per ben, fyra ben = **50 bp** per cykel vid noll basis. **Stress 2,5×** (alla fyra komponenter) = 125 bp (bokfört 124,2 bp: kostnaderna är andelar av ett krympande värde, så budgeten är en övre gräns inom 1 bp). Ingen BNB-rabatt, inga maker-order. |
| Markprisbaserat riskstopp | Varje hållen dag: marginalkvot (`basis_costs.margin_ratio`) vid dagens **högsta markpris** (markPriceKlines), underhållsnivå antagen **50 %**. Är kvoten ≥ **0,8** någon dag stängs båda benen vid nästa öppning (full kostnad) och myntet är platt resten av cykeln. Stoppet redovisas, och varje utlöst stopp ger **REJECT** (kriterium 5). Saknas markpris för en hållen dag är körningen `OGILTIG`. |
| Likviditetstak och minsta storlek | Positionen får vara högst **2 %** av seriens medianvolym (kassabokens tak) i USD över de senaste 20 verifierade handelsdagarna till och med beslutsdagen (volym i kontrakt × 10 USD). Färre än 20 handelsdagar eller överskriden gräns: platt. Minsta position 10 000 USD per mynt (ett kontrakt högst 0,1 %). |
| Kontraktsstorlek | Serien måste ha härledd median mellan 9,5 och 10,5 USD (`coinm-implied-contract-size.json`), annars platt (0 av 135 idag). |
| Jämförelse 1 (kontanter) | Årlig avkastning (CAGR) för **kassabokens totalvärde** `(V_slut / 140 000)^(365/1273) − 1`, över hela spannet 2021-03-27 till 2024-09-20 (1 273 dagar, inklusive platta perioder) ska överstiga **3 %**, samma gräns som i H-0020 (ungefär snittet för amerikanska 3-månadersväxlar 2021–2024; gränsen är ett förhandslåst närmevärde och inte en ny datahämtning). Annars är kontanter bättre. |
| Jämförelse 2 (marknadsneutral) | Beta mot BTCUSDT spot, regressionen på kvartalscyklernas avkastning (BTC spot, öppning till öppning, samma datum), n = 14. |
| Slumpkontroll | Inte tillämpbar (positionen är utan riktningsval). I stället redovisas *noll-basis-kostnaden* (50 bp) som referens för alla cyklers kostnad. |

## Cykelkalender (låst)

Genererad ur universumtabellen (`coinm-pit-series.json`) och `universe_at`; inga priser används. Beslut på föregående förfallsdag, inträde nästa dag, utträde sju kalenderdagar före serien förfall.
Cykel 2 är platt för alla mynt eftersom 0924-serien 2021 saknar daterad annons. Sista beslutsdag är 2024-06-28 (inom det biasfria fönstret 2021-03-26 till 2024-08-13).

| Cykel | Serie (förfall) | Beslutsdag (stängning, förfallsdagen före) | Inträde (fyllning 00:00 UTC) | Utträde (fyllning 00:00 UTC, kalenderdag förfall − 7) | Valbara underliggande vid beslutsdagen | Dagar i position | Kontanter före inträde (dagar) |
|---|---|---|---|---|---|---|---|
| 1 | 2021-06-25 | 2021-03-26 | 2021-03-27 | 2021-06-18 | alla sju | 83 | – |
| 2 | 2021-09-24 | 2021-06-25 | 2021-06-26 | 2021-09-17 | **ingen (serien saknar daterad annons): platt** | 83 | 8 |
| 3 | 2021-12-31 | 2021-09-24 | 2021-09-25 | 2021-12-24 | alla sju | 90 | 8 |
| 4 | 2022-03-25 | 2021-12-31 | 2022-01-01 | 2022-03-18 | alla sju | 76 | 8 |
| 5 | 2022-06-24 | 2022-03-25 | 2022-03-26 | 2022-06-17 | alla sju | 83 | 8 |
| 6 | 2022-09-30 | 2022-06-24 | 2022-06-25 | 2022-09-23 | alla sju | 90 | 8 |
| 7 | 2022-12-30 | 2022-09-30 | 2022-10-01 | 2022-12-23 | alla sju | 83 | 8 |
| 8 | 2023-03-31 | 2022-12-30 | 2022-12-31 | 2023-03-24 | alla sju | 83 | 8 |
| 9 | 2023-06-30 | 2023-03-31 | 2023-04-01 | 2023-06-23 | alla sju | 83 | 8 |
| 10 | 2023-09-29 | 2023-06-30 | 2023-07-01 | 2023-09-22 | alla sju | 83 | 8 |
| 11 | 2023-12-29 | 2023-09-29 | 2023-09-30 | 2023-12-22 | alla sju | 83 | 8 |
| 12 | 2024-03-29 | 2023-12-29 | 2023-12-30 | 2024-03-22 | alla sju | 83 | 8 |
| 13 | 2024-06-28 | 2024-03-29 | 2024-03-30 | 2024-06-21 | alla sju | 83 | 8 |
| 14 | 2024-09-27 | 2024-06-28 | 2024-06-29 | 2024-09-20 | alla sju | 83 | 8 |

Antal cykler **n = 14** (13 med positioner, 1 platt). Hela spannet är 1 273 dagar (3,49 år), detsamma som i H-0022.

## Kassaboken: två syntetiska cykler räknade för hand

Kassaboken är **identisk med H-0022:s** och använder samma `ledger_run` (test `test_ledger_exempel_vinst_och_forlust_tva_cykler`). De åtta dagarna i kontanter mellan utträde och inträde ändrar inte aritmetiken, eftersom kontanter inte ger ränta. Siffrorna nedan är syntetiska och oförändrade. Kostnader: spot 0,100 %, termin taker 0,050 %, glidning 5 bp per ben. Kontraktsstorlek 10 USD.

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

Samma som H-0022. Positionerna för de sju mynten rör sig ihop (samma börs, samma regim, samma kalender), och cyklerna är kvartal. Dagsavkastningen i en säkrad kassa-och-termin är nästan en jämn
upplupen basis, så ett dagligt t-värde vore kraftigt överskattat jämfört med de **14** oberoende utfallen. Därför är beslutsstatistiken lagd på cykelnivå:

* En observation per cykel, **ur kassaboken**: `r_k = V_slut / V_start − 1` för cykel k (hela portföljen; platta platser och kontanter ger 0 för sin del; den platta cykeln 2 ger exakt 0). Samma `r_k` används för t, beta och CAGR.
* t = medelvärde(`r_k`) / (std(`r_k`) / √14), med n−1 = 13 frihetsgrader.
* Kravet är **max(2,85; Student-t-kvantilen med 13 frihetsgrader för p = 0,05/23)** = max(2,85; **3,45**) = **3,45** (3,4452 med fyra decimaler). 2,85 är Bonferronikravet för N = 23
  (`python -m traderlab krav 23`, 2,8518); 3,45 är det strängare kravet för så få observationer (`scipy.stats.t.ppf(1 − 0,05/23, 13)`). Båda är beräknade utan att något utfall lästs.
* Redovisas utan att styra beslutet: bootstrap-intervall för medelavkastningen (cyklerna omsamplas, 10 000 dragningar, fast frö 0), antal positiva cykler, per mynt och per år, in- och utträdesbasis,
  och ett dagligt Newey-West-t som är **uttryckligen inte beslutsgrundande**.
* Beta mot BTC beräknas på samma 14 cykler (BTC spot, `open` till `open` över samma `F_k` till `F_{k+1}`) och redovisas med konfidensintervall; kriteriet nedan använder punktskattningen.

Ett positivt resultat med så få oberoende utfall är svagt bevis även om kriterierna klaras: det betyder bara att idén får granskas och prövas på den orörda perioden och på papper.

## Beslutskriterier (spår C, bestämda nu)

`MORE_RESEARCH` om **alla** gäller, annars `REJECT`:

1. t över de 14 cyklerna ≥ **3,45** (N = 23, Bonferronikrav 2,85, skärpt till t-kvantilen för 13 frihetsgrader).
2. Avkastning med **2,5 gånger** kostnaderna > 0 (sammanvägd över alla cykler).
3. |beta mot BTCUSDT spot| ≤ **0,2** (cykelregressionen).
4. Årlig avkastning (CAGR) för kassabokens totalvärde över hela spannet, inklusive platta perioder och kontanter, > **3 %**.
5. **Inget riskstopp utlöst** (marginalkvot aldrig ≥ 0,8) och ingen likvidation.

Godkänt betyder bara att idén får granskas och sedan testas på slutprovet (2025-01 till 2026-09) och på papper. Det betyder inte att strategin tjänar pengar framåt.

## Datakrav (annars `OGILTIG`, inget beslut, aldrig `MORE_RESEARCH`)

1. Verifierade dagsstaplar (checksumma, SHA-256 mot manifest där luckor fyllts, grannkontroll enligt `gapcheck.combined`) för terminsserien och spoten på varje inträdes- och utträdesdag för varje position.
2. Markpris (daglig high) för terminsserien varje hållen dag.
3. En saknad stapel eller **nollvolym på fyllningsdagen** (terminen eller spoten) för en position som redan beslutats, vid **inträde eller utträde**: `OGILTIG` (`basis_costs.InvalidFill`), aldrig dold som platt. En saknad stapel eller ingen handel på **beslutsdagen** gör däremot bara myntet platt den cykeln, eftersom beslutet då aldrig fattades.
4. Minst **46** av 91 möjliga mynt-cykler (7 × 13) handlade, och minst **10** av de 13 cyklerna med minst **4** handlade mynt. Annars för få observationer: `OGILTIG`. **Täckningsmätningen i PR #121 når 63 mynt-cykler och exakt 10 cykler som mest, utan marginal** (övre gräns vid minsta position 10 000 USD): en körning kan därför fortfarande bli `OGILTIG`.
5. Inga arkiv från 2025-01-01 eller senare har öppnats (test).
6. Universumtabellen är den som ligger på huvudgrenen vid registreringen (`research/universe/coinm-pit-series.json`) och cykelkalendern nedan reproduceras exakt med `h0022_coverage.cycle_calendar(rows, "rullning_b")` (test).
7. Luckor fylls aldrig med sista kända värde eller ersättare. En ogiltig körning redovisas som en ny rad och försöket räknas.

## Kända antaganden och svagheter (skrivna i förväg)

* **Idén valdes efter H-0022:s volymdiagnos** och klarar täckningen på exakt gränsen (10 av 10 cykler). Det är en designfrihet som gör ett positivt resultat mindre trovärdigt, och ett nytt försök med högre krav.
* **H-0020 är REJECT** på BTC och ETH, samma börs och delvis samma period (2021–2024); H-0022 blev OGILTIG. Resultatet förväntas vara korrelerat med H-0020. Priserna för dessa mynt är också sedda i H-0014 till H-0021 (USDT-terminer).
* **Få och korrelerade utfall:** 14 kvartalscykler (13 med positioner). Ett REJECT, `OGILTIG` eller `MORE_RESEARCH` med låg styrka är det troliga. Cykelkalendern ger regimer (2021 uppgång, 2022 nedgång, 2023–24 återhämtning) som kan avgöra resultatet.
* **Åtta dagar i kontanter utan ränta i varje cykel** sänker avkastningen på hela kapitalet jämfört med en tidtabell utan väntan. Det är konservativt men inte realistiskt.
* **Likviditet:** serien är nu den närmaste, men volymen faller kraftigt över tid (2021 ofta 10–30 miljoner USD per mynt och dag, från 2022 ofta under en miljon), och likviditetstaket gör många mynt-cykler platta (datakrav 4).
* **Helgfyllning:** inträdet sker lördag 00:00 UTC. Spread och glidning på helger kan vara större än antagna 5 bp per ben.
* **Spread och glidning är ett antagande** (5 bp per ben), inte en mätning. Stresstestet 2,5× ska visa om slutsatsen vänder.
* **Kontraktsstorlek 10 USD** är datahärledd, inte en Binance-källa per kontrakt. Marginalnivån (50 %) och stoppet 0,8 är antaganden: underhållsnivåerna höjdes stegvis 2021-02 till 2021-05 och stegen är inte arkiverade.
* **Avgifter:** taker 0,050 % hela perioden och spot 0,100 % utan rabatt är konservativa; verkliga nivåer kan ha varit lägre.
* **Utträdet 176 timmar före förfall** innebär en basisrest som inte har konvergerat. Den ingår i utfallet. Avräkningsfönstrets motsägelse undviks.
* **Motpartsrisk och exekvering** finns inte i ett backtest: börsfallissemang (FTX 2022), uttagsstopp, ADL, två order som inte fylls exakt samtidigt, och att Binance kan ha ändrat regler.
* **Kontantgränsen 3 %** är ett närmevärde (ungefär snittet för amerikanska 3-månadersväxlar 2021–2024).

## Före körning

Motorkoden skrivs i en **separat PR** och granskas innan något körs. Den ska återanvända `pit_universe.universe_at`, `basis_costs.pre_expiry_cycle`, `ledger_run` och `margin_ratio`, `gapcheck.combined`
och läsare med periodgränser, och ha tester för:

1. look-ahead (beslut använder bara data till och med beslutsdagen `D_k`) och slutprovsskyddet (ingen fil från 2025 eller senare öppnas),
2. att cykelkalendern ovan reproduceras exakt, inklusive den platta cykeln 2 och de åtta dagarna i kontanter,
3. att serier utan daterad annons, utan verifierad stapel beslutsdagen, med luckor eller över likviditetsgränsen blir platta och aldrig ersätts,
4. att augustiluckan 2023 fylls bara med verifierade dagsstaplar och märks i proveniensen,
5. separata spot- och terminspriser vid in- och utträde, och att `pre_expiry_cycle` (inte avräkning) används,
6. riskstoppets definition (marginalkvot ≥ 0,8 på dagens högsta markpris stänger vid nästa öppning, ett stopp ger REJECT),
7. kostnadsbudgeten 50 bp (125 bp i stress) vid noll basis, att en saknad fyllningsstapel ger `OGILTIG`, och att kassaboken kedjar `V` exakt över kontantperioderna.

Datahämtning för strategin görs först i den PR:en och först efter att den här registreringen är granskad och mergad.

## Källor

`research/rullning-b-kandidat.md`, `research/universe/rullning-b-rapport.md`, `research/coverage/rullning-b-datatackning.json`, `research/universe/h0022-datatackning.md`,
`research/universe/coinm-pit-rapport.md`, `research/universe/coinm-pit-series.json`, `research/universe/h0022-kostnad-antaganden.md`, `research/universe/coinm-implied-contract-size.json`,
`research/h0022-protokoll.md`, `engine/traderlab/pit_universe.py`, `engine/traderlab/basis_costs.py`, `engine/traderlab/h0022_coverage.py`, `engine/traderlab/data/gapcheck.py`.
