# Agentlab R004: första autonoma forskningskörningen

Utforskande. Allt här är upprepade försök på samma data och inget är ett bekräftande test. Slutprovet 2025+ är aldrig läst.

* Idéer genererade: **200**, utvalda: **36** (+ 8 negativa kontroller), utvärderade versioner inklusive iterationer: **42**
* Domslut: {'REJECT': 36, 'ITERATED': 6}
* Försök som räknas (inklusive grannparametrar): **770**, registrerade experiment: **173**
* Sub-agenter som skapades: **149**, parallella arbetsprocesser: **4**, tid: 80.2 s
* Slutprovsblickar i den förseglade datan (valideringsåret/slutåret): 5

## Vad systemet lärde sig

* ML slog den enkla tumregeln xs_mom i 2 av 13 körningar (discovery).
* Negativa kontroller: 8 slumpstrategier, 0 gick vidare förbi discovery (falsklarmsfrekvens 0/8).
* Vanligaste dödsorsaker: inte skild från slumpen (33); olönsam med 2,5 gånger kostnaderna (23); deflated Sharpe 0.00 med 15.0 effektiva försök (10); deflated Sharpe 0.01 med 15.0 effektiva försök (8); ingen rimlig ändring finns (4)

## Familjer

| Familj | Testade | REJECT | Gick vidare | Bästa discovery-Sharpe |
|---|---|---|---|---|
| bab | 1 | 1 | 1 | 1.70 |
| donchian | 1 | 1 | 0 | 1.32 |
| funding_carry | 8 | 8 | 0 | 0.71 |
| funding_fade | 1 | 1 | 0 | -0.59 |
| lowvol | 1 | 1 | 0 | 0.47 |
| ml_xs | 13 | 8 | 0 | 1.40 |
| mtf_trend | 1 | 1 | 0 | 0.49 |
| pairs | 1 | 1 | 0 | -0.62 |
| trend_ma | 1 | 1 | 0 | 0.69 |
| ts_mom | 2 | 2 | 0 | 0.47 |
| vol_regime | 1 | 1 | 0 | -0.25 |
| vol_shock | 1 | 1 | 0 | 0.58 |
| xs_mom | 9 | 8 | 0 | 1.25 |
| xs_rev | 1 | 1 | 0 | -0.89 |

## Kandidater (efter debatt)

| Nyckel | Idé | Iter | Disc-Sharpe | Slutdom | Poäng | Huvudinvändning |
|---|---|---|---|---|---|---|
| `108fb9dfbab8` | bab(vt=0.2, k=60, q=0.3, rebal=7, uni=50) | 0 | 1.70 | REJECT | 51.8 |  |
| `71dd6e73beb6` | ml_xs(model=ridge, h=1, q=0.3, retrain=90, uni=30) | 0 | -0.29 | REJECT | None | weak_disc: Discovery-Sharpe -0.29 är för låg. |
| `7f0e63fe9594` | xs_mom(skip=3, q=0.2, rebal=14, uni=30, vt=0.2, k=90) | 0 | -0.05 | REJECT | None | weak_disc: Discovery-Sharpe -0.05 är för låg. |
| `828eed5084a9` | funding_carry(vt=0.2, k=7, q=0.3, rebal=7, uni=30) | 0 | 0.39 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 26% av fallen (p= |
| `33d113825485` | ts_mom(long_only=False, vt=0, uni=5, k=80) | 0 | 0.28 | REJECT | None | weak_disc: Discovery-Sharpe 0.28 är för låg. |
| `35c4bf21e658` | trend_ma(vt=0, n=50, basket=10) | 0 | 0.69 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 59% av fallen (p= |
| `261ecb0215fc` | xs_rev(q=0.2, rebal=5, uni=20, vt=0, k=5) | 0 | -0.89 | REJECT | None | weak_disc: Discovery-Sharpe -0.89 är för låg. |
| `1c66336e44df` | lowvol(vt=0, k=90, q=0.2, rebal=14, uni=30) | 0 | 0.47 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 15% av fallen (p= |
| `9ce75bb12daf` | mtf_trend(vt=0.15, ks=[10, 30, 90], basket=10) | 0 | 0.49 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 49% av fallen (p= |
| `b80e10a4d56f` | donchian(vt=0.15, n=20, basket=10) | 0 | 1.32 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 12% av fallen (p= |
| `3a2cc9a8722a` | funding_fade(k=3, z=1.5, hold=7, uni=30) | 0 | -0.59 | REJECT | None | drawdown: Största nedgång -95% på discovery. |
| `ac553030b5e8` | pairs(lb=20, z_in=1.5, z_out=0.0, npairs=3) | 0 | -0.62 | REJECT | None | leakage: Vikterna ändras av framtida data (maxskillnad 0.333): läckag |
| `68d1686656ee` | vol_regime(base=ts_mom, k_vol=20, mode=low, k=60, uni=30) | 0 | -0.25 | REJECT | None | weak_disc: Discovery-Sharpe -0.25 är för låg. |
| `d04389fc68c9` | vol_shock(z=3.0, mode=follow, hold=3, uni=50) | 0 | 0.58 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 23% av fallen (p= |
| `fa584c72d55b` | ml_xs(model=ens, h=3, q=0.2, retrain=90, uni=30) | 0 | 1.06 | ITERATED |  | ml_no_better_than_simple: ML (1.06) slår inte tumregeln xs_mom (0.93). Behåll det enkl |
| `60beab4c2edb` | ml_xs(model=rf, h=1, q=0.3, retrain=60, uni=30) | 0 | 0.38 | ITERATED |  | ml_no_better_than_simple: ML (0.38) slår inte tumregeln xs_mom (0.84). Behåll det enkl |
| `9094376567ea` | ml_xs(model=lgbm_prob, h=3, q=0.2, retrain=90, uni=30) | 0 | 1.14 | ITERATED |  | selection_bias: Deflated Sharpe 0.34 med 15 effektiva oberoende försök (av 7 |
| `38d1f1fc9626` | ml_xs(model=lgbm_prob, h=3, q=0.3, retrain=90, uni=30) | 0 | 0.70 | ITERATED |  | ml_no_better_than_simple: ML (0.70) slår inte tumregeln xs_mom (1.51). Behåll det enkl |
| `35eacbd54a3c` | ml_xs(model=ridge, h=1, q=0.2, retrain=90, uni=30) | 0 | -0.79 | REJECT | None | weak_disc: Discovery-Sharpe -0.79 är för låg. |
| `f41fe82da176` | ml_xs(model=ridge, h=3, q=0.3, retrain=60, uni=30) | 0 | 1.40 | REJECT | None | ml_no_better_than_simple: ML (1.40) slår inte tumregeln xs_mom (1.51). Behåll det enkl |
| `f3c43c24000e` | ml_xs(model=ridge, h=3, q=0.2, retrain=90, uni=30) | 0 | 0.90 | REJECT | None | ml_no_better_than_simple: ML (0.90) slår inte tumregeln xs_mom (0.93). Behåll det enkl |
| `856ccb9a3b6a` | xs_mom(skip=1, q=0.2, rebal=14, uni=20, vt=0.2, k=60) | 0 | -0.25 | REJECT | None | weak_disc: Discovery-Sharpe -0.25 är för låg. |
| `17bc2f0757ff` | xs_mom(skip=3, q=0.3, rebal=3, uni=30, vt=0.2, k=7) | 0 | -0.24 | REJECT | None | weak_disc: Discovery-Sharpe -0.24 är för låg. |
| `041952d89f61` | xs_mom(skip=1, q=0.3, rebal=14, uni=50, vt=0, k=60) | 0 | 0.08 | REJECT | None | weak_disc: Discovery-Sharpe 0.08 är för låg. |
| `08dadf4f9f5f` | funding_carry(vt=0, k=3, q=0.2, rebal=3, uni=50) | 0 | 0.28 | REJECT | None | weak_disc: Discovery-Sharpe 0.28 är för låg. |
| `a59f1cf2d10b` | xs_mom(skip=1, q=0.2, rebal=7, uni=20, vt=0.2, k=90) | 0 | -0.13 | REJECT | None | weak_disc: Discovery-Sharpe -0.13 är för låg. |
| `560fd86dade2` | funding_carry(vt=0.2, k=30, q=0.3, rebal=7, uni=30) | 0 | -0.56 | REJECT | None | weak_disc: Discovery-Sharpe -0.56 är för låg. |
| `29bc6ee37a82` | xs_mom(skip=0, q=0.2, rebal=7, uni=30, vt=0, k=14) | 0 | 0.73 | ITERATED |  | tail_risk: Svansen är tung: CVaR5 -4.6%, sämsta dag -12.8%. |
| `e3fa0cd38ca6` | xs_mom(skip=1, q=0.2, rebal=3, uni=30, vt=0.2, k=14) | 0 | 1.25 | REJECT | None | selection_bias: Deflated Sharpe 0.41 med 15 effektiva oberoende försök (av 7 |
| `24c2a0a4fa80` | xs_mom(skip=0, q=0.3, rebal=14, uni=30, vt=0.2, k=60) | 0 | 0.21 | REJECT | None | weak_disc: Discovery-Sharpe 0.21 är för låg. |
| `b1162662ddd5` | funding_carry(vt=0, k=30, q=0.2, rebal=3, uni=50) | 0 | 0.25 | REJECT | None | weak_disc: Discovery-Sharpe 0.25 är för låg. |
| `5ad5972ba49b` | funding_carry(vt=0.2, k=7, q=0.3, rebal=3, uni=30) | 0 | 0.09 | REJECT | None | weak_disc: Discovery-Sharpe 0.09 är för låg. |
| `39a597f0cde6` | funding_carry(vt=0, k=7, q=0.2, rebal=3, uni=30) | 0 | 0.38 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 30% av fallen (p= |
| `2bca23e0cceb` | funding_carry(vt=0, k=30, q=0.3, rebal=7, uni=50) | 0 | -0.09 | REJECT | None | weak_disc: Discovery-Sharpe -0.09 är för låg. |
| `d44ccfbc8af1` | funding_carry(vt=0, k=3, q=0.3, rebal=3, uni=50) | 0 | 0.71 | REJECT | None | selection_bias: Deflated Sharpe 0.14 med 15 effektiva oberoende försök (av 7 |
| `8fac032a197c` | ts_mom(long_only=False, vt=0.15, uni=5, k=20) | 0 | 0.47 | REJECT | None | indistinguishable_from_luck: Slumpmässig timing ger lika bra resultat i 18% av fallen (p= |
| `cd98b6e8ba94` | (kontroll) placebo(seed=100, q=0.2, rebal=3, uni=30) | 0 | -0.94 | REJECT | None | weak_disc: Discovery-Sharpe -0.94 är för låg. |
| `6d167dc3c138` | (kontroll) placebo(seed=101, q=0.2, rebal=7, uni=30) | 0 | -0.24 | REJECT | None | weak_disc: Discovery-Sharpe -0.24 är för låg. |
| `0f415b1b59df` | (kontroll) placebo(seed=102, q=0.2, rebal=3, uni=30) | 0 | -1.79 | REJECT | None | weak_disc: Discovery-Sharpe -1.79 är för låg. |
| `cd952e677e73` | (kontroll) placebo(seed=103, q=0.2, rebal=7, uni=30) | 0 | 1.12 | REJECT | None | param_unstable: Grannparametrar är klart sämre: kanten sitter i en parameter |
| `9870d0c5fe44` | (kontroll) placebo(seed=104, q=0.2, rebal=3, uni=30) | 0 | -1.07 | REJECT | None | weak_disc: Discovery-Sharpe -1.07 är för låg. |
| `a5ef4bcaa794` | (kontroll) placebo(seed=105, q=0.2, rebal=7, uni=30) | 0 | -0.74 | REJECT | None | weak_disc: Discovery-Sharpe -0.74 är för låg. |
| `03b499cfae9d` | (kontroll) placebo(seed=106, q=0.2, rebal=3, uni=30) | 0 | -1.37 | REJECT | None | weak_disc: Discovery-Sharpe -1.37 är för låg. |
| `2b4a36b0f1c6` | (kontroll) placebo(seed=107, q=0.2, rebal=7, uni=30) | 0 | 0.07 | REJECT | None | weak_disc: Discovery-Sharpe 0.07 är för låg. |
| `80f79228f807` | ml_xs(model=ens, h=5, q=0.2, retrain=90, uni=30) | 1 | 0.98 | REJECT | None | ml_no_better_than_simple: ML (0.98) slår inte tumregeln xs_mom (1.27). Behåll det enkl |
| `62a877ce0588` | ml_xs(model=rf, h=3, q=0.3, retrain=60, uni=30) | 1 | 1.21 | REJECT | None | ml_no_better_than_simple: ML (1.21) slår inte tumregeln xs_mom (1.51). Behåll det enkl |
| `0d80b931cba5` | ml_xs(model=lgbm_prob, h=5, q=0.2, retrain=90, uni=30) | 1 | 0.03 | REJECT | None | weak_disc: Discovery-Sharpe 0.03 är för låg. |
| `43c8cd634567` | ml_xs(model=lgbm_prob, h=5, q=0.3, retrain=90, uni=30) | 1 | 0.45 | ITERATED |  | ml_no_better_than_simple: ML (0.45) slår inte tumregeln xs_mom (1.56). Behåll det enkl |
| `4903600c43fc` | xs_mom(skip=0, q=0.2, rebal=7, uni=30, vt=0.2, k=14) | 1 | 1.09 | REJECT | None | selection_bias: Deflated Sharpe 0.32 med 15 effektiva oberoende försök (av 7 |
| `735b57803b0f` | ml_xs(model=ridge, h=5, q=0.3, retrain=90, uni=30) | 2 | 0.88 | REJECT | None | ml_no_better_than_simple: ML (0.88) slår inte tumregeln xs_mom (1.56). Behåll det enkl |

## Lovande kandidater

Inga. Allt blev REJECT eller dog på vägen. Det är ett helt acceptabelt utfall.

## Kända problem

* Inga fel från agenterna.
