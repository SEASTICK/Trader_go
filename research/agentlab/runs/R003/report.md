# Agentlab R003: första autonoma forskningskörningen

Utforskande. Allt här är upprepade försök på samma data och inget är ett bekräftande test. Slutprovet 2025+ är aldrig läst.

* Idéer genererade: **150**, utvalda: **30** (+ 8 negativa kontroller), utvärderade versioner inklusive iterationer: **32**
* Domslut: {'REJECT': 30, 'ITERATED': 2}
* Försök som räknas (inklusive grannparametrar): **544**, registrerade experiment: **122**
* Sub-agenter som skapades: **117**, parallella arbetsprocesser: **4**, tid: 65.2 s
* Slutprovsblickar i den förseglade datan (valideringsåret/slutåret): 4

## Vad systemet lärde sig

* ML slog den enkla tumregeln xs_mom i 1 av 5 körningar (discovery).
* Negativa kontroller: 8 slumpstrategier, 0 gick vidare förbi discovery (falsklarmsfrekvens 0/8).
* Vanligaste dödsorsaker: inte skild från slumpen (27); olönsam med 2,5 gånger kostnaderna (19); deflated Sharpe 0.00 med 14.3 effektiva försök (10); ingen rimlig ändring finns (5); deflated Sharpe 0.01 med 14.3 effektiva försök (5)

## Familjer

| Familj | Testade | REJECT | Gick vidare | Bästa discovery-Sharpe |
|---|---|---|---|---|
| bab | 1 | 1 | 0 | 0.72 |
| donchian | 2 | 2 | 0 | 0.96 |
| ensemble_rank | 5 | 5 | 1 | 1.71 |
| funding_carry | 1 | 1 | 0 | 0.94 |
| funding_fade | 1 | 1 | 0 | -0.00 |
| lowvol | 2 | 2 | 0 | 0.91 |
| ml_xs | 5 | 3 | 0 | 1.27 |
| mtf_trend | 2 | 2 | 0 | 0.85 |
| pairs | 1 | 1 | 0 | -1.26 |
| trend_ma | 1 | 1 | 0 | 0.89 |
| ts_mom | 1 | 1 | 0 | 0.27 |
| vol_regime | 1 | 1 | 0 | -0.27 |
| vol_shock | 1 | 1 | 0 | -0.82 |
| xs_mom | 6 | 6 | 0 | 1.02 |
| xs_rev | 2 | 2 | 0 | -1.79 |

## Kandidater (efter debatt)

| Nyckel | Idé | Iter | Disc-Sharpe | Slutdom | Poäng | Huvudinvändning |
|---|---|---|---|---|---|---|
| `2d3d4d5026e5` | ensemble_rank(members=['xs_mom', 'funding_carry', 'lowvol'], q=0.2, re | 0 | 1.71 | REJECT | 55.8 |  |
| `59427e56d85e` | ensemble_rank(members=['xs_mom', 'xs_rev', 'bab'], q=0.3, rebal=3) | 0 | 0.80 | REJECT | None | selection_bias: Deflated Sharpe 0.16 med 14 effektiva oberoende försök (av 5 |
| `7da0e0754215` | xs_mom(skip=3, q=0.3, rebal=7, uni=50, vt=0.2, k=90) | 0 | -0.43 | REJECT | None | weak_disc: Discovery-Sharpe -0.43 är för låg. |
| `20eb6622fa58` | xs_rev(q=0.2, rebal=2, uni=30, vt=0, k=7) | 0 | -2.22 | REJECT | None | weak_disc: Discovery-Sharpe -2.22 är för låg. |
| `7254b3889fb0` | lowvol(vt=0.2, k=40, q=0.3, rebal=14, uni=30) | 0 | 0.91 | REJECT | None | selection_bias: Deflated Sharpe 0.20 med 14 effektiva oberoende försök (av 5 |
| `1347dae07a3c` | donchian(vt=0, n=40, basket=10) | 0 | 0.96 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 47% av fallen (p= |
| `276a77db4812` | mtf_trend(vt=0.15, ks=[20, 60, 180], basket=5) | 0 | 0.85 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 24% av fallen (p= |
| `53f492c11f78` | ml_xs(model=mlp, h=1, q=0.2, retrain=90, uni=30) | 0 | 0.45 | ITERATED |  | high_turnover: Omsättning 328x per år äter kostnader. |
| `9190134e68d7` | bab(vt=0.2, k=180, q=0.3, rebal=7, uni=50) | 0 | 0.72 | REJECT | None | selection_bias: Deflated Sharpe 0.13 med 14 effektiva oberoende försök (av 5 |
| `3d9b8ffbb802` | funding_carry(vt=0, k=14, q=0.3, rebal=3, uni=30) | 0 | 0.94 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 11% av fallen (p= |
| `678bfce8593c` | pairs(lb=20, z_in=2.5, z_out=0.0, npairs=6) | 0 | -1.26 | REJECT | None | leakage: Vikterna ändras av framtida data (maxskillnad 0.167): läckag |
| `f572a23de072` | funding_fade(k=7, z=2.0, hold=7, uni=50) | 0 | -0.00 | REJECT | None | drawdown: Största nedgång -92% på discovery. |
| `2c6df3942e82` | trend_ma(vt=0.15, n=200, basket=2) | 0 | 0.89 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 23% av fallen (p= |
| `9e60b8bdc7e3` | ts_mom(long_only=False, vt=0, uni=10, k=80) | 0 | 0.27 | REJECT | None | weak_disc: Discovery-Sharpe 0.27 är för låg. |
| `6be5a5e07b90` | vol_shock(z=3.0, mode=fade, hold=3, uni=50) | 0 | -0.82 | REJECT | None | drawdown: Största nedgång -99% på discovery. |
| `119fe6fff8ee` | vol_regime(base=ts_mom, k_vol=20, mode=low, k=30, uni=30) | 0 | -0.27 | REJECT | None | weak_disc: Discovery-Sharpe -0.27 är för låg. |
| `ed4638b0aaff` | ensemble_rank(members=['xs_mom', 'funding_carry', 'lowvol'], q=0.3, re | 0 | 1.28 | REJECT | None | selection_bias: Deflated Sharpe 0.38 med 14 effektiva oberoende försök (av 5 |
| `89ead85f5439` | ensemble_rank(members=['funding_carry', 'lowvol', 'bab'], q=0.3, rebal | 0 | 1.29 | REJECT | None | selection_bias: Deflated Sharpe 0.39 med 14 effektiva oberoende försök (av 5 |
| `decf78427a8e` | ensemble_rank(members=['funding_carry', 'lowvol', 'bab'], q=0.2, rebal | 0 | 1.21 | REJECT | None | tail_risk: Svansen är tung: CVaR5 -4.5%, sämsta dag -13.3%. |
| `977b8b09f618` | xs_mom(skip=0, q=0.2, rebal=3, uni=50, vt=0, k=120) | 0 | 0.47 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 21% av fallen (p= |
| `b12576e396e7` | xs_mom(skip=3, q=0.2, rebal=7, uni=20, vt=0.2, k=14) | 0 | 1.02 | REJECT | None | selection_bias: Deflated Sharpe 0.24 med 14 effektiva oberoende försök (av 5 |
| `d6d8f6bd361c` | xs_mom(skip=3, q=0.2, rebal=7, uni=30, vt=0, k=7) | 0 | 0.08 | REJECT | None | weak_disc: Discovery-Sharpe 0.08 är för låg. |
| `1ae762b211aa` | xs_mom(skip=0, q=0.2, rebal=14, uni=30, vt=0.2, k=60) | 0 | 0.00 | REJECT | None | weak_disc: Discovery-Sharpe 0.00 är för låg. |
| `bc64ad45c7c5` | xs_mom(skip=3, q=0.3, rebal=14, uni=30, vt=0.2, k=60) | 0 | -0.04 | REJECT | None | weak_disc: Discovery-Sharpe -0.04 är för låg. |
| `382d1253c48d` | mtf_trend(vt=0.15, ks=[10, 30, 90], basket=5) | 0 | 0.82 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 21% av fallen (p= |
| `aa8782e7f9b3` | ml_xs(model=lgbm, h=5, q=0.2, retrain=90, uni=30) | 0 | 0.30 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 20% av fallen (p= |
| `e16dd8d38cc9` | donchian(vt=0.15, n=80, basket=5) | 0 | 0.18 | REJECT | None | weak_disc: Discovery-Sharpe 0.18 är för låg. |
| `99cac0a48675` | lowvol(vt=0, k=20, q=0.2, rebal=14, uni=50) | 0 | 0.44 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 18% av fallen (p= |
| `bc95749962a7` | xs_rev(q=0.2, rebal=5, uni=30, vt=0, k=1) | 0 | -1.79 | REJECT | None | weak_disc: Discovery-Sharpe -1.79 är för låg. |
| `d70f5dba1c59` | ml_xs(model=ridge, h=5, q=0.3, retrain=60, uni=30) | 0 | 0.78 | REJECT | None | ml_no_better_than_simple: ML (0.78) slår inte tumregeln xs_mom (1.56). Behåll det enkl |
| `cd98b6e8ba94` | (kontroll) placebo(seed=100, q=0.2, rebal=3, uni=30) | 0 | -0.94 | REJECT | None | weak_disc: Discovery-Sharpe -0.94 är för låg. |
| `6d167dc3c138` | (kontroll) placebo(seed=101, q=0.2, rebal=7, uni=30) | 0 | -0.24 | REJECT | None | weak_disc: Discovery-Sharpe -0.24 är för låg. |
| `0f415b1b59df` | (kontroll) placebo(seed=102, q=0.2, rebal=3, uni=30) | 0 | -1.79 | REJECT | None | weak_disc: Discovery-Sharpe -1.79 är för låg. |
| `cd952e677e73` | (kontroll) placebo(seed=103, q=0.2, rebal=7, uni=30) | 0 | 1.12 | REJECT | None | param_unstable: Grannparametrar är klart sämre: kanten sitter i en parameter |
| `9870d0c5fe44` | (kontroll) placebo(seed=104, q=0.2, rebal=3, uni=30) | 0 | -1.07 | REJECT | None | weak_disc: Discovery-Sharpe -1.07 är för låg. |
| `a5ef4bcaa794` | (kontroll) placebo(seed=105, q=0.2, rebal=7, uni=30) | 0 | -0.74 | REJECT | None | weak_disc: Discovery-Sharpe -0.74 är för låg. |
| `03b499cfae9d` | (kontroll) placebo(seed=106, q=0.2, rebal=3, uni=30) | 0 | -1.37 | REJECT | None | weak_disc: Discovery-Sharpe -1.37 är för låg. |
| `2b4a36b0f1c6` | (kontroll) placebo(seed=107, q=0.2, rebal=7, uni=30) | 0 | 0.07 | REJECT | None | weak_disc: Discovery-Sharpe 0.07 är för låg. |
| `bad2ed0dfa50` | ml_xs(model=mlp, h=3, q=0.2, retrain=90, uni=30) | 1 | 1.27 | ITERATED |  | selection_bias: Deflated Sharpe 0.38 med 14 effektiva oberoende försök (av 5 |
| `2f74bad8e366` | ml_xs(model=mlp, h=5, q=0.2, retrain=90, uni=30) | 2 | 0.35 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 17% av fallen (p= |

## Lovande kandidater

Inga. Allt blev REJECT eller dog på vägen. Det är ett helt acceptabelt utfall.

## Kända problem

* Inga fel från agenterna.
