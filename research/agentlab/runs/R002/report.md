# Agentlab R002: första autonoma forskningskörningen

Utforskande. Allt här är upprepade försök på samma data och inget är ett bekräftande test. Slutprovet 2025+ är aldrig läst.

* Idéer genererade: **150**, utvalda: **30** (+ 8 negativa kontroller), utvärderade versioner inklusive iterationer: **31**
* Domslut: {'REJECT': 29, 'PROMISING': 1, 'ITERATED': 1}
* Försök som räknas (inklusive grannparametrar): **375**, registrerade experiment: **82**
* Sub-agenter som skapades: **108**, parallella arbetsprocesser: **4**, tid: 19.8 s
* Slutprovsblickar i den förseglade datan (valideringsåret/slutåret): 3

## Vad systemet lärde sig

* ML slog den enkla tumregeln xs_mom i 1 av 1 körningar (discovery).
* Negativa kontroller: 8 slumpstrategier, 0 gick vidare förbi discovery (falsklarmsfrekvens 0/8).
* Vanligaste dödsorsaker: inte skild från slumpen (30); olönsam med 2,5 gånger kostnaderna (16); deflated Sharpe 0.00 med 13.0 effektiva försök (9); deflated Sharpe 0.02 med 13.0 effektiva försök (4); ingen rimlig ändring finns (4)

## Familjer

| Familj | Testade | REJECT | Gick vidare | Bästa discovery-Sharpe |
|---|---|---|---|---|
| bab | 1 | 1 | 0 | 1.32 |
| donchian | 1 | 1 | 0 | 0.11 |
| ensemble_rank | 2 | 1 | 1 | 1.74 |
| funding_carry | 6 | 6 | 0 | 0.94 |
| funding_fade | 1 | 1 | 0 | -1.39 |
| lowvol | 1 | 1 | 0 | 0.37 |
| ml_xs | 1 | 1 | 1 | 1.65 |
| mtf_trend | 1 | 1 | 0 | 0.82 |
| pairs | 1 | 1 | 0 | -0.83 |
| trend_ma | 6 | 6 | 0 | 0.95 |
| ts_mom | 5 | 5 | 0 | 1.04 |
| vol_regime | 2 | 2 | 0 | 0.79 |
| vol_shock | 1 | 1 | 0 | 0.64 |
| xs_mom | 1 | 0 | 0 | 0.61 |
| xs_rev | 1 | 1 | 0 | -1.68 |

## Kandidater (efter debatt)

| Nyckel | Idé | Iter | Disc-Sharpe | Slutdom | Poäng | Huvudinvändning |
|---|---|---|---|---|---|---|
| `610bac07a444` | ensemble_rank(members=['xs_mom', 'funding_carry', 'lowvol'], q=0.3, re | 0 | 1.74 | PROMISING | 66.9 |  |
| `0051738937c5` | ml_xs(model=lgbm, h=3, q=0.3, retrain=60, uni=30) | 0 | 1.65 | REJECT | 48.3 | ml_no_better_than_simple: ML (1.65) slår inte tumregeln xs_mom (1.51). Behåll det enkl |
| `1399020269c6` | funding_carry(vt=0, k=7, q=0.2, rebal=3, uni=50) | 0 | 0.16 | REJECT | None | weak_disc: Discovery-Sharpe 0.16 är för låg. |
| `b392ed621e7d` | trend_ma(vt=0.15, n=50, basket=5) | 0 | 0.95 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 26% av fallen (p= |
| `21702fbc0491` | ts_mom(long_only=True, vt=0.15, uni=5, k=80) | 0 | 0.14 | REJECT | None | weak_disc: Discovery-Sharpe 0.14 är för låg. |
| `5d24d119a900` | lowvol(vt=0, k=90, q=0.3, rebal=14, uni=50) | 0 | 0.37 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 16% av fallen (p= |
| `ca61a35e45c9` | donchian(vt=0, n=80, basket=5) | 0 | 0.11 | REJECT | None | drawdown: Största nedgång -93% på discovery. |
| `c06e40fcb5b6` | mtf_trend(vt=0, ks=[20, 60, 180], basket=5) | 0 | 0.82 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 34% av fallen (p= |
| `bfe0c4ac988e` | xs_rev(q=0.3, rebal=3, uni=30, vt=0.2, k=5) | 0 | -1.68 | REJECT | None | weak_disc: Discovery-Sharpe -1.68 är för låg. |
| `0f6acdf9d385` | bab(vt=0.2, k=90, q=0.2, rebal=7, uni=30) | 0 | 1.32 | REJECT | None | selection_bias: Deflated Sharpe 0.44 med 13 effektiva oberoende försök (av 3 |
| `c3c32c09d34b` | funding_fade(k=7, z=2.0, hold=3, uni=30) | 0 | -1.39 | REJECT | None | drawdown: Största nedgång -99% på discovery. |
| `269dbe5519ff` | pairs(lb=20, z_in=1.5, z_out=0.5, npairs=6) | 0 | -0.83 | REJECT | None | leakage: Vikterna ändras av framtida data (maxskillnad 0.167): läckag |
| `47f7352a2da9` | xs_mom(skip=1, q=0.3, rebal=3, uni=50, vt=0.2, k=14) | 0 | 0.61 | ITERATED |  | selection_bias: Deflated Sharpe 0.11 med 13 effektiva oberoende försök (av 3 |
| `27fcfdb40901` | vol_regime(base=ts_mom, k_vol=20, mode=high, k=60, uni=30) | 0 | 0.66 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 33% av fallen (p= |
| `050384bce67c` | vol_shock(z=2.0, mode=fade, hold=3, uni=50) | 0 | 0.64 | REJECT | None | high_turnover: Omsättning 282x per år äter kostnader. |
| `c03050811847` | funding_carry(vt=0, k=14, q=0.3, rebal=7, uni=50) | 0 | 0.41 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 29% av fallen (p= |
| `7e474a16cdca` | funding_carry(vt=0.2, k=14, q=0.2, rebal=7, uni=30) | 0 | -0.28 | REJECT | None | weak_disc: Discovery-Sharpe -0.28 är för låg. |
| `50f5c2d41f49` | funding_carry(vt=0, k=7, q=0.3, rebal=3, uni=30) | 0 | 0.94 | REJECT | None | selection_bias: Deflated Sharpe 0.23 med 13 effektiva oberoende försök (av 3 |
| `35840c2b5fbd` | funding_carry(vt=0.2, k=14, q=0.2, rebal=7, uni=50) | 0 | 0.21 | REJECT | None | weak_disc: Discovery-Sharpe 0.21 är för låg. |
| `812502bdeae4` | funding_carry(vt=0, k=7, q=0.2, rebal=7, uni=30) | 0 | 0.49 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 25% av fallen (p= |
| `e949ce60b89f` | trend_ma(vt=0.15, n=50, basket=10) | 0 | 0.62 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 55% av fallen (p= |
| `4700e199c34e` | trend_ma(vt=0, n=200, basket=10) | 0 | 0.22 | REJECT | None | weak_disc: Discovery-Sharpe 0.22 är för låg. |
| `bb7584cf8286` | ensemble_rank(members=['xs_mom', 'xs_rev', 'bab'], q=0.2, rebal=3) | 0 | 1.31 | REJECT | None | selection_bias: Deflated Sharpe 0.43 med 13 effektiva oberoende försök (av 3 |
| `6be56afb0eee` | ts_mom(long_only=True, vt=0.15, uni=5, k=160) | 0 | -0.05 | REJECT | None | weak_disc: Discovery-Sharpe -0.05 är för låg. |
| `c6fad4ee5e74` | trend_ma(vt=0, n=20, basket=2) | 0 | 0.56 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 33% av fallen (p= |
| `5c7be0d87560` | ts_mom(long_only=True, vt=0.15, uni=10, k=80) | 0 | 0.11 | REJECT | None | weak_disc: Discovery-Sharpe 0.11 är för låg. |
| `cc7da2befafe` | ts_mom(long_only=True, vt=0.15, uni=10, k=40) | 0 | 1.04 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 30% av fallen (p= |
| `957b9eac894b` | ts_mom(long_only=True, vt=0.15, uni=5, k=10) | 0 | 0.62 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 44% av fallen (p= |
| `9a855dabba77` | trend_ma(vt=0.15, n=200, basket=10) | 0 | 0.26 | REJECT | None | weak_disc: Discovery-Sharpe 0.26 är för låg. |
| `068d6651fdbf` | trend_ma(vt=0.15, n=100, basket=5) | 0 | 0.06 | REJECT | None | weak_disc: Discovery-Sharpe 0.06 är för låg. |
| `cd98b6e8ba94` | (kontroll) placebo(seed=100, q=0.2, rebal=3, uni=30) | 0 | -0.94 | REJECT | None | weak_disc: Discovery-Sharpe -0.94 är för låg. |
| `6d167dc3c138` | (kontroll) placebo(seed=101, q=0.2, rebal=7, uni=30) | 0 | -0.24 | REJECT | None | weak_disc: Discovery-Sharpe -0.24 är för låg. |
| `0f415b1b59df` | (kontroll) placebo(seed=102, q=0.2, rebal=3, uni=30) | 0 | -1.79 | REJECT | None | weak_disc: Discovery-Sharpe -1.79 är för låg. |
| `cd952e677e73` | (kontroll) placebo(seed=103, q=0.2, rebal=7, uni=30) | 0 | 1.12 | REJECT | None | param_unstable: Grannparametrar är klart sämre: kanten sitter i en parameter |
| `9870d0c5fe44` | (kontroll) placebo(seed=104, q=0.2, rebal=3, uni=30) | 0 | -1.07 | REJECT | None | weak_disc: Discovery-Sharpe -1.07 är för låg. |
| `a5ef4bcaa794` | (kontroll) placebo(seed=105, q=0.2, rebal=7, uni=30) | 0 | -0.74 | REJECT | None | weak_disc: Discovery-Sharpe -0.74 är för låg. |
| `03b499cfae9d` | (kontroll) placebo(seed=106, q=0.2, rebal=3, uni=30) | 0 | -1.37 | REJECT | None | weak_disc: Discovery-Sharpe -1.37 är för låg. |
| `2b4a36b0f1c6` | (kontroll) placebo(seed=107, q=0.2, rebal=7, uni=30) | 0 | 0.07 | REJECT | None | weak_disc: Discovery-Sharpe 0.07 är för låg. |
| `e557e6fa0403` | vol_regime(base=xs_mom, k_vol=20, mode=low, k=30, uni=30) | 1 | 0.79 | REJECT | None | selection_bias: Deflated Sharpe 0.17 med 13 effektiva oberoende försök (av 3 |

## Lovande kandidater

* ensemble_rank(members=['xs_mom', 'funding_carry', 'lowvol'], q=0.3, rebal=3) [PROMISING, poäng 66.9]

## Kända problem

* Inga fel från agenterna.
