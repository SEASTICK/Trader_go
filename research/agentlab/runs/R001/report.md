# Agentlab R001: första autonoma forskningskörningen

Utforskande. Allt här är upprepade försök på samma data och inget är ett bekräftande test. Slutprovet 2025+ är aldrig läst.

* Idéer genererade: **150**, utvalda: **30** (+ 8 negativa kontroller), utvärderade versioner inklusive iterationer: **35**
* Domslut: {'REJECT': 30, 'ITERATED': 5}
* Försök som räknas (inklusive grannparametrar): **201**, registrerade experiment: **43**
* Sub-agenter som skapades: **125**, parallella arbetsprocesser: **4**, tid: 19.1 s
* Slutprovsblickar i den förseglade datan (valideringsåret/slutåret): 0

## Vad systemet lärde sig

* ML slog den enkla tumregeln xs_mom i 1 av 2 körningar (discovery).
* Negativa kontroller: 8 slumpstrategier, 0 gick vidare förbi discovery (falsklarmsfrekvens 0/8).
* Vanligaste dödsorsaker: inte skild från slumpen (30); olönsam med 2,5 gånger kostnaderna (18); deflated Sharpe 0.00 med 15.9 effektiva försök (14); deflated Sharpe 0.04 med 15.9 effektiva försök (4); ingen rimlig ändring finns (4)

## Familjer

| Familj | Testade | REJECT | Gick vidare | Bästa discovery-Sharpe |
|---|---|---|---|---|
| bab | 1 | 1 | 0 | 0.78 |
| donchian | 1 | 1 | 0 | 0.96 |
| ensemble_rank | 5 | 3 | 0 | 1.52 |
| funding_carry | 7 | 6 | 0 | 0.89 |
| funding_fade | 1 | 1 | 0 | -0.61 |
| lowvol | 1 | 1 | 0 | 0.21 |
| ml_xs | 2 | 1 | 0 | 1.55 |
| mtf_trend | 1 | 1 | 0 | 0.68 |
| pairs | 1 | 1 | 0 | -1.32 |
| trend_ma | 5 | 4 | 0 | 0.88 |
| ts_mom | 1 | 1 | 0 | 0.68 |
| vol_regime | 1 | 1 | 0 | 1.19 |
| vol_shock | 1 | 1 | 0 | -0.78 |
| xs_mom | 6 | 6 | 0 | 0.52 |
| xs_rev | 1 | 1 | 0 | -2.00 |

## Kandidater (efter debatt)

| Nyckel | Idé | Iter | Disc-Sharpe | Slutdom | Poäng | Huvudinvändning |
|---|---|---|---|---|---|---|
| `1e5d86fb7081` | xs_mom(skip=0, q=0.2, rebal=3, uni=30, vt=0.2, k=120) | 0 | 0.36 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 22% av fallen (p= |
| `035fe48512b4` | funding_carry(vt=0.2, k=14, q=0.3, rebal=7, uni=50) | 0 | 0.10 | REJECT | None | weak_disc: Discovery-Sharpe 0.10 är för låg. |
| `f915e6991d82` | trend_ma(vt=0, n=100, basket=2) | 0 | 0.44 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 52% av fallen (p= |
| `123800b28405` | ensemble_rank(members=['funding_carry', 'lowvol', 'bab'], q=0.2, rebal | 0 | 1.08 | ITERATED |  | selection_bias: Deflated Sharpe 0.23 med 16 effektiva oberoende försök (av 1 |
| `2a9c14525d0b` | ts_mom(long_only=False, vt=0, uni=5, k=160) | 0 | 0.68 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 32% av fallen (p= |
| `5a31a06ad38a` | xs_rev(q=0.2, rebal=2, uni=30, vt=0.2, k=3) | 0 | -2.00 | REJECT | None | weak_disc: Discovery-Sharpe -2.00 är för låg. |
| `cbc20fd20dc6` | donchian(vt=0.15, n=40, basket=5) | 0 | 0.96 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 30% av fallen (p= |
| `7121ab6b68f7` | lowvol(vt=0, k=40, q=0.2, rebal=7, uni=30) | 0 | 0.21 | REJECT | None | weak_disc: Discovery-Sharpe 0.21 är för låg. |
| `a740d00e97d9` | mtf_trend(vt=0.15, ks=[20, 60, 180], basket=10) | 0 | 0.68 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 41% av fallen (p= |
| `79c521890543` | ml_xs(model=lgbm, h=3, q=0.3, retrain=90, uni=30) | 0 | 1.21 | ITERATED |  | ml_no_better_than_simple: ML (1.21) slår inte tumregeln xs_mom (1.51). Behåll det enkl |
| `be7cf3d8a71a` | vol_regime(base=ts_mom, k_vol=20, mode=high, k=30, uni=30) | 0 | 1.19 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 11% av fallen (p= |
| `839deeffa5cb` | bab(vt=0, k=180, q=0.3, rebal=14, uni=30) | 0 | 0.78 | REJECT | None | selection_bias: Deflated Sharpe 0.12 med 16 effektiva oberoende försök (av 1 |
| `ccaf50b9e6e1` | pairs(lb=40, z_in=2.0, z_out=0.5, npairs=6) | 0 | -1.32 | REJECT | None | leakage: Vikterna ändras av framtida data (maxskillnad 0.167): läckag |
| `04474bcc8b0b` | funding_fade(k=7, z=1.5, hold=7, uni=30) | 0 | -0.61 | REJECT | None | drawdown: Största nedgång -93% på discovery. |
| `0ce3119d0d39` | vol_shock(z=3.0, mode=fade, hold=3, uni=30) | 0 | -0.78 | REJECT | None | drawdown: Största nedgång -97% på discovery. |
| `50b6cdd942f3` | xs_mom(skip=1, q=0.3, rebal=7, uni=30, vt=0, k=90) | 0 | 0.32 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 19% av fallen (p= |
| `44f2ddca506b` | funding_carry(vt=0.2, k=30, q=0.2, rebal=3, uni=30) | 0 | -0.70 | REJECT | None | weak_disc: Discovery-Sharpe -0.70 är för låg. |
| `d9bc17524b39` | funding_carry(vt=0, k=3, q=0.3, rebal=7, uni=50) | 0 | 0.71 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 11% av fallen (p= |
| `fa9caa28ed9f` | xs_mom(skip=3, q=0.3, rebal=14, uni=50, vt=0.2, k=14) | 0 | 0.52 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 19% av fallen (p= |
| `bc0966debb54` | xs_mom(skip=0, q=0.2, rebal=3, uni=20, vt=0.2, k=120) | 0 | -0.24 | REJECT | None | weak_disc: Discovery-Sharpe -0.24 är för låg. |
| `0d897a5028c6` | xs_mom(skip=3, q=0.3, rebal=7, uni=50, vt=0, k=90) | 0 | -0.31 | REJECT | None | weak_disc: Discovery-Sharpe -0.31 är för låg. |
| `f29d416cf6bb` | funding_carry(vt=0, k=14, q=0.3, rebal=7, uni=30) | 0 | 0.89 | ITERATED |  | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 12% av fallen (p= |
| `bbbdfe68b142` | xs_mom(skip=3, q=0.2, rebal=3, uni=50, vt=0.2, k=120) | 0 | 0.14 | REJECT | None | weak_disc: Discovery-Sharpe 0.14 är för låg. |
| `5c009b8a9a02` | funding_carry(vt=0.2, k=14, q=0.2, rebal=3, uni=30) | 0 | -0.50 | REJECT | None | weak_disc: Discovery-Sharpe -0.50 är för låg. |
| `923f8c6cdcba` | funding_carry(vt=0.2, k=3, q=0.3, rebal=7, uni=50) | 0 | 0.38 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 25% av fallen (p= |
| `60a32b8d445f` | trend_ma(vt=0, n=20, basket=10) | 0 | 0.46 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 70% av fallen (p= |
| `a12a69b3ce7a` | ensemble_rank(members=['xs_mom', 'funding_carry', 'lowvol'], q=0.2, re | 0 | 1.52 | REJECT | None | selection_bias: Deflated Sharpe 0.46 med 16 effektiva oberoende försök (av 1 |
| `d3391b1624d5` | trend_ma(vt=0, n=50, basket=5) | 0 | 0.60 | REJECT | None | drawdown: Största nedgång -91% på discovery. |
| `b01872143813` | ensemble_rank(members=['xs_mom', 'xs_rev', 'bab'], q=0.2, rebal=7) | 0 | 0.89 | ITERATED |  | tail_risk: Svansen är tung: CVaR5 -4.0%, sämsta dag -13.3%. |
| `f438a88c0e73` | trend_ma(vt=0, n=50, basket=2) | 0 | 0.88 | ITERATED |  | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 13% av fallen (p= |
| `cd98b6e8ba94` | (kontroll) placebo(seed=100, q=0.2, rebal=3, uni=30) | 0 | -0.94 | REJECT | None | weak_disc: Discovery-Sharpe -0.94 är för låg. |
| `6d167dc3c138` | (kontroll) placebo(seed=101, q=0.2, rebal=7, uni=30) | 0 | -0.24 | REJECT | None | weak_disc: Discovery-Sharpe -0.24 är för låg. |
| `0f415b1b59df` | (kontroll) placebo(seed=102, q=0.2, rebal=3, uni=30) | 0 | -1.79 | REJECT | None | weak_disc: Discovery-Sharpe -1.79 är för låg. |
| `cd952e677e73` | (kontroll) placebo(seed=103, q=0.2, rebal=7, uni=30) | 0 | 1.12 | REJECT | None | param_unstable: Grannparametrar är klart sämre: kanten sitter i en parameter |
| `9870d0c5fe44` | (kontroll) placebo(seed=104, q=0.2, rebal=3, uni=30) | 0 | -1.07 | REJECT | None | weak_disc: Discovery-Sharpe -1.07 är för låg. |
| `a5ef4bcaa794` | (kontroll) placebo(seed=105, q=0.2, rebal=7, uni=30) | 0 | -0.74 | REJECT | None | weak_disc: Discovery-Sharpe -0.74 är för låg. |
| `03b499cfae9d` | (kontroll) placebo(seed=106, q=0.2, rebal=3, uni=30) | 0 | -1.37 | REJECT | None | weak_disc: Discovery-Sharpe -1.37 är för låg. |
| `2b4a36b0f1c6` | (kontroll) placebo(seed=107, q=0.2, rebal=7, uni=30) | 0 | 0.07 | REJECT | None | weak_disc: Discovery-Sharpe 0.07 är för låg. |
| `fe3f386819ae` | ensemble_rank(members=['funding_carry', 'lowvol', 'bab'], q=0.3, rebal | 1 | 1.30 | REJECT | None | selection_bias: Deflated Sharpe 0.35 med 15 effektiva oberoende försök (av 2 |
| `3e965c3d9604` | ml_xs(model=ridge, h=3, q=0.3, retrain=90, uni=30) | 1 | 1.55 | REJECT | None | ml_no_better_than_simple: ML (1.55) slår inte tumregeln xs_mom (1.51). Behåll det enkl |
| `e5caf966d23a` | funding_carry(vt=0, k=30, q=0.3, rebal=7, uni=30) | 1 | 0.18 | REJECT | None | weak_disc: Discovery-Sharpe 0.18 är för låg. |
| `18bc45c1b7e4` | ensemble_rank(members=['xs_mom', 'xs_rev', 'bab'], q=0.3, rebal=7) | 1 | 0.71 | REJECT | None | selection_bias: Deflated Sharpe 0.10 med 15 effektiva oberoende försök (av 2 |
| `e2c80fd152a3` | trend_ma(vt=0.15, n=50, basket=2) | 1 | 0.63 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 29% av fallen (p= |

## Lovande kandidater

Inga. Allt blev REJECT eller dog på vägen. Det är ett helt acceptabelt utfall.

## Kända problem

* Inga fel från agenterna.
