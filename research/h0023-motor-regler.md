# H-0023: strategimotorn, regel för regel

Motorn är `engine/traderlab/h0023.py` (plus delad kod i `basis_costs.py`, `h0022_coverage.py`, `pit_universe.py`, `data/gapcheck.py`). Den är byggd och testad med **syntetiska data**
(`engine/tests/test_h0023.py`). **Den har inte körts mot historik, ingen resultatfil finns och inget slutprov har lästs.** `h0023.run()` kräver `--confirm-registered-run` och att H-0023
finns i det committade registret; en körning görs först efter granskning av motorn och av datahämtningen.

Varje låst regel i `research/h0023-protokoll.md` är kopplad till kod och minst ett test. Provet `test_reglertabellen_pekar_på_kod_och_tester_som_finns` kontrollerar att de nämnda testerna och funktionerna finns.

| Protokollregel | Kod | Test |
|---|---|---|
| Sju mynt (ADA, BCH, BNB, DOT, LINK, LTC, XRP), BTC och ETH ingår inte | `SEVEN`, `_decide_coin` | `test_beslutet_ändras_inte_av_något_efter_beslutsdagen_utom_fyllningsstaplarna` |
| Beslutsdagar 2021-03-26 till 2024-06-28, biasfritt fönster, 14 cykler, cykel 2 platt | `cycle_calendar`, `_check_cycle` | `test_kalendern_har_14_cykler_inklusive_platt_cykel_2_och_sista_utträdet_x14`, `test_kalendertabellen_i_protokollet_är_exakt_rullning_b_ur_universumtabellen`, `test_överlevnadsbias_sju_ensamma_är_efterhandsurval_till_sista_förfallet_hos_de_fyra` |
| Serie per cykel: närmast efter föregående förfall, ingen ersättare, 0924-serien utan annons är platt | `cycle_calendar`, `universe_at`, `_decide_coin` | `test_annonserad_men_ännu_ohandlad_serie_är_inte_valbar`, `test_saknad_beslutsdagsstapel_färre_än_20_dagar_eller_fel_kontraktsstorlek_gör_myntet_platt_inte_ogiltigt` |
| Inträde: beslut på förfallsdagens avslutade stapel, fyllning nästa 00:00 UTC | `_check_cycle`, `entry_fill_utc` | `test_kalendern_har_14_cykler_inklusive_platt_cykel_2_och_sista_utträdet_x14`, `test_utträdet_är_öppningen_kalenderdagen_sju_dagar_före_förfall_inte_168_timmar_och_inte_stängning` |
| Utträde 00:00 UTC sju kalenderdagar före förfall (176 timmar) | `exit_fill_utc`, `_fill_prices` | `test_alla_fjorton_utträden_är_fredagar_176_timmar_före_förfallet` |
| Beslut bara med data till och med beslutsdagen (före fyllningen) | `_decide_coin`, `liquidity_cap_usd` | `test_beslutet_ändras_inte_av_något_efter_beslutsdagen_utom_fyllningsstaplarna`, `test_rullningsbeslut_vid_0000_ändras_inte_av_utträdesdagens_saknade_eller_nollvolymstapel`, `test_likviditetstaket_använder_bara_dagar_till_och_med_beslutsdagen` |
| Åtta dagar i kontanter utan ränta mellan utträde och inträde; platt cykel står still | `simulate` (dagsvärde), `_daily_series` | `test_kassaboken_kedjar_v_återinvesterar_och_ligger_8_dagar_i_kontanter_mellan_cyklerna` |
| Priser: `open` i 1d-stapeln 00:00 UTC, samma `open_time`, separata spot- och terminspriser | `_bar`, `_fill_prices`, `pre_expiry_cycle` | `test_spot_och_termin_har_separata_priser_vid_in_och_utträde`, `test_open_time_0100_på_fyllningsdagen_är_ogiltig_eftersom_dagsstapeln_måste_vara_00_00` |
| Markprisdagar: inträdesdagen till dagen före utträdesdagen | `held_mark_days`, `_fill_prices` | `test_sista_markprisdag_är_dagen_före_utträdesdagen`, `test_saknad_fyllnings_eller_hållen_dagsstapel_för_en_beslutad_position_är_ogiltig_aldrig_platt` |
| Hela kapitalet och coin-marginalen, heltalskontrakt avrundade ned, hävstång ≤ 1 | `pre_expiry_cycle` | `test_pre_expiry_hävstång_högst_1_och_avrundningen_redovisas`, `test_hela_kapitalet_räknas_och_kostnaderna_minskar_slutvärdet` |
| Självfinansierande kassabok: start 140 000, `A = min(V/7, tak)`, minst 10 000, vinster återinvesteras, överskott som kontanter | `position_size`, `ledger_run`, `simulate` | `test_kassaboken_kedjar_v_återinvesterar_och_ligger_8_dagar_i_kontanter_mellan_cyklerna`, `test_storleken_är_densamma_som_kassabokens_enda_storleksregel_och_taket_begränsar`, `test_ledger_exempel_vinst_och_forlust_tva_cykler` |
| Kostnader: 50 bp per cykel (fyra ben), stress 2,5× = 125 bp | `Costs`, `pre_expiry_cycle` | `test_nollbasis_kostar_50_bp_och_stress_125_bp_per_position_oberoende_av_prisriktningen`, `test_pre_expiry_noll_basis_kostar_exakt_budgeten_50_bp_med_alla_fyra_ben` |
| Markprisbaserat riskstopp: marginalkvot ≥ 0,8 vid dagens högsta markpris, stäng vid nästa öppning, ett stopp ger REJECT | `margin_ratio`, `simulate`, `evaluate` | `test_riskstopp_stänger_vid_nästa_öppning_med_full_kostnad_och_standardgränsen_0_8_utlöses_aldrig_vid_full_täckning`, `test_stopp_ger_reject_via_kriteriet_och_aldrig_morgonbeslut`, `test_marginalkvoten_är_oberoende_av_priset_vid_full_täckning` |
| Likviditetstak 2 % av 20 handelsdagars medianvolym, minsta position 10 000 USD | `liquidity_cap_usd`, `position_size` | `test_storleken_är_densamma_som_kassabokens_enda_storleksregel_och_taket_begränsar`, `test_likviditetströsklarna_500k_och_1m_och_medianen_använder_bara_dagar_till_beslutsdagen` |
| Kontraktsstorlek 9,5–10,5 USD per serie, annars platt | `_decide_coin` (`SIZE_RANGE`) | `test_saknad_beslutsdagsstapel_färre_än_20_dagar_eller_fel_kontraktsstorlek_gör_myntet_platt_inte_ogiltigt` |
| Cykelavkastning `r_k = V(T_k)/V(F_k) − 1`, `T_14 = X_14`, BTC över samma intervall, ingen `F_15` | `cycle_windows`, `paired_observations`, `evaluate` | `test_sista_cykelavkastningen_och_btc_använder_slutpunkten_x14_utan_f15_eller_2025_data`, `test_cykelstatistik_t_beta_cagr_och_beslut_på_de_14_cyklerna_med_x14_som_slutpunkt` |
| Statistik: t på cykelnivå, krav max(Bonferroni för N = 23, t-kvantilen 13 frihetsgrader) = 3,45 | `cycle_t`, `t_required` | `test_beslutsmatrisen_more_research_bara_om_alla_fem_kriterier_gäller`, `test_n_23_och_t_gränserna_är_beräknade_och_samma_i_protokoll_och_register` |
| CAGR över hela spannet (1 273 dagar), beta mot BTCUSDT, stressad avkastning | `evaluate` | `test_cykelstatistik_t_beta_cagr_och_beslut_på_de_14_cyklerna_med_x14_som_slutpunkt`, `test_giltig_syntetisk_körning_ger_siffror_och_beslut_enligt_kriterierna` |
| Beslutskriterier: `MORE_RESEARCH` bara om alla fem gäller, annars `REJECT` | `decide` | `test_beslutsmatrisen_more_research_bara_om_alla_fem_kriterier_gäller` |
| Datakrav 1–3: verifierade staplar på fyllningsdagar, markpris varje hållen dag, saknad fyllning är `OGILTIG` och aldrig platt | `_fill_prices`, `InvalidRun` | `test_saknad_fyllnings_eller_hållen_dagsstapel_för_en_beslutad_position_är_ogiltig_aldrig_platt`, `test_saknad_eller_nollvolym_fyllningsstapel_efter_beslut_är_ogiltig_inte_platt` |
| Datakrav 4: minst 46 av 91 mynt-cykler och minst 10 av 13 cykler med minst 4 mynt, annars `OGILTIG` | `evaluate` | `test_datakrav_4_ger_ogiltig_utan_prestandasiffror_och_aldrig_more_research` |
| Datakrav 5: inga arkiv från 2025 eller senare öppnas | `assert_before_holdout`, `h0022_coverage._load` (periodgränser) | `test_staplar_från_slutprovet_i_panelen_ger_ogiltig_och_läsarna_stänger_2024_10`, `test_läsaren_öppnar_inte_filer_från_2025` |
| Datakrav 6: universumtabellen och kalendern reproduceras exakt | `cycle_calendar` | `test_kalendertabellen_i_protokollet_är_exakt_rullning_b_ur_universumtabellen` |
| Datakrav 7: luckor fylls aldrig med ersättare, bara verifierade dagsfiler | `gapcheck.combined` (via `load_panel`) | `test_observed_markerar_saknad_dag_och_nollvolym_och_fyller_bara_med_verifierad_dagsstapel` |
| Datakrav 8: verifierad BTCUSDT-stapel för varje `F_k` och `T_k` | `evaluate` | `test_saknad_btc_stapel_för_beta_ger_ogiltig` |
| En ogiltig körning ger inga prestandasiffror och aldrig `MORE_RESEARCH` | `evaluate`, `run` | `test_datakrav_4_ger_ogiltig_utan_prestandasiffror_och_aldrig_more_research` |
| Körningen kräver bekräftelse och registrering, ingen resultatfil skapas av tester | `run` | `test_körningen_kräver_bekräftelse_och_skriver_ingen_fil_utan_den` |

## Protokollets "Före körning", punkt för punkt

1. **Look-ahead och slutprovsskydd:** raderna om beslut och 2025 ovan.
2. **Kalendern reproduceras exakt, inklusive platt cykel 2 och åtta dagar kontanter:** raderna om kalender och kontanter.
3. **Platta mynt aldrig ersatta:** `_decide_coin` returnerar bara ja eller nej per mynt, och `test_saknad_beslutsdagsstapel_färre_än_20_dagar_eller_fel_kontraktsstorlek_gör_myntet_platt_inte_ogiltigt`.
4. **Augustiluckan 2023 fylls bara med verifierade dagsstaplar:** `gapcheck.combined` och `test_observed_markerar_saknad_dag_och_nollvolym_och_fyller_bara_med_verifierad_dagsstapel`.
5. **Separata priser och `pre_expiry_cycle`:** `test_spot_och_termin_har_separata_priser_vid_in_och_utträde`.
6. **Riskstoppets definition:** raderna om riskstopp.
7. **Kostnadsbudget, saknad fyllningsstapel ger `OGILTIG`, kassabokens kedjning:** raderna om kostnader, datakrav 1–3 och kassabok.

## Avgränsningar (öppet)

* **Laddaren `load_panel` är inte provkörd på riktiga data.** BTCUSDT-spot och övriga spotmånader för strategin hämtas först efter att motorn är granskad. Saknas en fil blir mynt-cykeln platt (före beslut) eller `OGILTIG` (beslutad position, BTC för beta).
* Rapporteringen av dagligt Newey-West-t (inte beslutsgrundande) bygger på en dagsserie med öppning-till-öppning-värden ur kassaboken; den är provad bara för att den finns och är ändlig, inte mot ett facit.
* Per mynt, per år, in- och utträdesbasis och bootstrap-intervall redovisas via `positions` och `mean_cycle_return_ci` i resultatet. De är rena sammanställningar och styr inget beslut.
* Datakrav 4 har standardvärdena 46 och 10; parametrarna finns bara så att syntetiska tester med färre cykler kan pröva logiken.
