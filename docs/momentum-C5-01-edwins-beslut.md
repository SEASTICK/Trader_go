# H-0017 C5-01: Edwins beslut om funding vid intrastapellikvidation

Datum: 2026-11-04. Underlag: [C5-granskningen av b131ff4](momentum-C5-granskning-b131ff4.md) (fynd C5-01) och
[Codex ordningsbeslut](momentum-C5-01-ordningsbeslut.md), som fastslog att frågan kräver Edwins beslut och inte valde
något alternativ själv.

**Fråga.** När marginalprövningen inom stapeln träffar (§8.3: C efter betald och före mottagen mellanfunding, mark_low
för long) är träfftiden okänd. Vilka av stapelns exakta mellanhändelser ska stå i ledgerns `funding_net`, och vad tar
`liquidation_adjustment`?

**Edwins beslut (2026-11-04, i chatten med Claude):** alternativ 1, "Ingen bokförs". Ingen mellanhändelse i en stapel
med intrastapelträff bokförs som betald eller mottagen funding. Var och en redovisas separat som olöst vid likvidation
med exakt tid och belopp, och nollställningen tar resten.

## Konvention som implementeras

- Prövningsunderlaget är oförändrat enligt §8.3 och hålls skilt från ledgern. Det redovisas som underlags-C, E_low, MM
  och mark_low, och C4:s likvidationspost dokumenterar underlaget.
- Ledgern: funding före träffstapeln och öppningens A/B-funding står kvar. Ingen av stapelns mellanhändelser bokförs.
  Kontot efter öppningen nollställs: C = q = avg = 0. Justeringen är C4:s `adjustment_delta` minus de betalningar som
  bara fanns i underlaget. Det motsvarar hela kontot efter öppningen. Avstämningen C = deposit + realized − costs −
  funding_net + liquidation_adjustment − q·avg = 0 håller.
- Spåret: varje mellanhändelse får kategorin `funding_unresolved` med exakt tid, belopp och om den ingick i
  underlaget. Likvidationen har tiden "okänd inom stapeln". Ingen ordning mellan träffen och fundingtiderna påstås.
- Utan träff gäller oförändrat kronologisk bokföring (§8.3, D18). Efter en känd likvidation (gappunkt eller tidigare
  stapel) får senare event kategorin `funding_absorbed`.
- Ekonomiskt utfall är oförändrat: E = C = q = 0, absorberande tillstånd, samma §4-dagsserie och C6.
- §15-redovisningen av betald/mottagen funding byggs senare. De olösta beloppen ska då redovisas separat, inte som
  betald eller mottagen funding.

Detta är ett dokumenterat tillägg för en lucka i det frysta protokollet, inte en protokolländring. Protokollet,
registret och tidigare resultat är oförändrade.
