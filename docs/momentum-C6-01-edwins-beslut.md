# H-0017 C6-01: Edwins beslut om §10.2-bounden vid likvidation

Datum: 2026-11-04. Underlag: [beslutsunderlaget](momentum-C6-01-beslutsunderlag.md) och
[Codex granskning av underlaget](momentum-C6-01-granskning-underlag.md), som formulerade de fyra valfrågorna.
Frågorna ställdes till Edwin i chatten med Claude med Codex alternativ och utan förval eller rekommendation.

**Edwins svar (2026-11-04): 1 = H1, 2 = I1, 3 = G1, 4 = P1.**

1. **H1:** vid intrastapelträff ingår high och low med q_open och C_high = C_post − Σmin(p_i, 0) respektive
   C_low = C_post − Σmax(p_i, 0). Alla olösta mellanevent används enbart hypotetiskt i bounden och bokförs aldrig
   (C5-01 består).
2. **I1:** negativa råvärden i träffstapelns valda boundpunkter före nollställningen behålls oklippta som signerade
   boundpunkter, även när drawdown blir under −100 %.
3. **G1:** ett negativt gap- eller öppningsprövningsvärde före känd öppningslikvidation ingår med sitt råa värde före
   likvidationsnollan.
4. **P1, placering och dokumentation (Codex formulering, godkänd):** vid intrastapelträff kommer likvidationsnollan
   efter den hypotetiska low-fasen. Vid öppningsträff kommer den efter C5:s gap-, A- och prövningssteg som faktiskt
   hunnit ske, med negativa punkter enligt G1. Faktisk close och terminal är 0. Peak och tidigare drawdownminimum
   behålls. Därefter gäller bara absorberande noll: inga gamla positionsextremer, affärer eller funding. Den
   hypotetiska punktordningen påstås inte vara en tidsordning mellan träff, extremer och funding. Alla mellanevent vid
   intrastapelträff förblir olösta i ledgern enligt C5-01. Valen dokumenteras som detta separata, länkade
   C6-01-tillägg med reservationen nedan. Det frysta protokollet och C5-01 skrivs inte om. Omfattningen är huvudmodell
   long/platt inom C6-uppdraget, inte ett legacybeslut.

## Reservation om konservativitet (från Codex granskning)

§10.2 motiverar high före low med positivt kapital. För en negativ trough gäller det omvända: en högre peak gör
drawdown mindre negativ, till exempel −32 800/101 000 − 1 = −669/505 men −32 800/120 000 − 1 = −191/150. Bounden
påstås därför inte vara bevisat strängast under −100 %. Valet ändrar inte C6 eller den ekonomiska klassificeringen
för huvudmodellen, eftersom varje likvidation i main gör C6 falskt enligt §13.2. Det ändrar redovisningen av
max_dd_bound.

## Vad detta inte gör

Detta är ingen protokolländring och ingen ändring av C5-01, ledgern, marginalunderlaget eller close-serien (§10.1). Det
godkänner ingen implementation. Codex granskar det dokumenterade svaret, därefter implementationen och den syntetiska
verifieringen.
