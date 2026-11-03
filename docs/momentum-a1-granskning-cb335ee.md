# Codex granskning av momentum A1 – cb335ee

Datum: 2026-11-03. Granskad revision: `cb335eec6b70002affc41b632b5931457e6a53fc`, diffbas `e55340a`.

**A1 är inte godkänd för A2.** Fyra kontraktsfynd behöver rättas och omgranskas före registrering. Ingen motorkod finns i leveransen; detta är metodfel/oklarheter som annars kan byggas in i implementationen. H-0013 REJECT och H-0016 är oförändrade.

## 1. [P1] En riskminskning kan bli ett köp efter gap

`docs/momentum-protokoll-A1.md:148–157` och invarianten på rad 320.

Avsikten fryser vikt, medan riskavsikter aldrig får öka enheter. Dessa regler är inte förenliga för alla öppningsgap. Syntetiskt: C=800, q=2, senaste mark_close=100 ger vikt 0,20. Ny cap och målvikt 0,195 utlöser riskminskning. Vid nästa öppning P=M=90 har vikten redan sjunkit till 0,183673. Den föreskrivna lösaren till den frysta vikten ger q_new=2,12329486533535 inklusive avgift, alltså ett **köp** på cirka 0,123295 enheter.

Följer motorn lösaren bryter den riskinvarianten; avvisar den varje sådant fall blir en legitim prisrörelse ett ogiltigt experiment. Lås en reduce-only-regel för riskavsikter vid utförandet: ingen ökning av |q|, behåll enheter om målet redan underskrids. Beskriv uttryckligen när denna regel går före exakt målvikt och hur hold/klippning loggas. Lägg till orakel för gap i båda riktningar och risk/normal-prioritet.

## 2. [P1] Funding får inte flyttas över fyllningstidpunkten

`docs/momentum-protokoll-A1.md:188`, tillsammans med eventordningen på raderna 174–177.

Villkoret abs(t−T)<60 sekunder gör en avräkning 2022-01-02 00:00:30 till en gränshändelse vid 00:00. I scenario A debiteras den då på gamla positionen **före** affären och påverkar storleken, trots att dess avräkningstid ligger efter affären. En händelse 23:59:30 kan i stället skjutas fram till nästa dag/mark_open. A/B behövs för samma tidsstämpel, men motiverar inte att distinkta tidsstämplar görs samtidiga. Inget dataunderlag har ännu visat att denna tolerans behövs.

Behåll exakt eventtid. Låt bara exakt samtidiga händelser omfattas av A/B. Avvikande tidsstämplar behöver en förregistrerad hantering som bevarar kronologin; antingen avvisas de vid datakontrollen eller hanteras med uttryckligt avgränsade mellanliggande pris-/positionsscenarier. De får inte flyttas bakåt och påverka tidigare fyllningar. Lägg till syntetiska ±30-sekundersfall, dagsgräns och första/sista tillåtna event.

## 3. [P1] T-regelns betalningsgräns är ingen konservativ Sharpe-gräns

`docs/momentum-protokoll-A1.md:189–197`, D05 och C3–C5 på raderna 303–310.

Regeln väljer lägre ekonomiskt utfall för main och högre för jämförelserna och hävdar att en tvetydighet bara kan göra MORE_RESEARCH svårare. Det följer inte för Sharpe. Syntetiska dagsavkastningar [0,010; 0,011; 0,009; 0,100] ger annualiserad Sharpe 13,7958. En extra kostnad som sänker sista avkastningen till 0,010 ger sämre avkastning men Sharpe 233,9872. Därmed kan "ogynnsam" funding för main höja dess kriterievärde, medan "gynnsam" funding för en kontroll kan sänka dess Sharpe. Samma principiella problem gäller t-statistik. Exemplet är ett matematiskt motexempel, inget strategiresultat.

Lås kompletta, tidsmässigt förenliga scenarier och bedöm de faktiska kriterierna i dessa. Om en konservativ Sharpe-gräns påstås måste den visas för det måttet; ett lokalt sämre fundingbelopp räcker inte. En fast prisapproximation kan beskrivas som en modell med känslighetskontroll, men inte som en bevisad ogynnsam gräns för alla kriterier. Lägg till motexemplet i oraklen och precisera beslutet när scenarier skiljer sig. Välj inte en gynnsam variant efter resultatet.

## 4. [P2] E_after och viktinvarianten behöver skilda fundingfaser

`docs/momentum-protokoll-A1.md:124`, eventsteg 5–7 på raderna 176–178 och rad 320.

§6 definierar E_after efter affär men före scenario B-funding; steg 7 sparar E_after först efter denna funding. Orakel O5 ger själv q=499,6003197442, M=P=100 och målvikt/cap 0,5. Affärens kapital är 99 920,06394884, men efter funding 4,99600319744 är kapitalet 99 915,06794564 och vikten 0,50002500125. Den överskrider cap+1e−12 vid den sparade after_fill-punkten och uppfyller inte §6:s identitet med det kapitalet.

Fundingdrift är redan tillåten i §7 och behöver inte i sig förbjudas. Lås separata namn och händelsefaser för kapital efter handel respektive efter funding, och ange exakt var målidentitet och cap kontrolleras. Alternativt krävs en gemensam lösare om cap uttryckligen ska gälla efter funding. Lägg till ett orakel som granskar båda faserna; lämna inte samma E_after med två definitioner.

## Besked om Claudes tre metodfrågor

- **Både scenario A och B måste klara kraven:** rimlig förregistrerad känslighetsgrind för exakt samtidiga event. Principen kan behållas; fynd 2–4 behöver först lösas.
- **Legacy-stop med mark-extrem medan positionen kan ha funnits:** rimlig sträng diagnostisk bound för okänd ordning mellan kontrakts- och markpris. Den får inte beskrivas som observerad drawdown eller flyttas in i affärsledgern som ett säkert faktiskt förlopp.
- **Fast 5 % underhållsmarginal:** kan behållas som uttrycklig forsknings-/stressmodell, med 0,5 % redovisat. Det är inte en verifiering av historiska Binance-villkor eller tillräckligt för framtida driftgodkännande. Det befintliga markprisunderlaget verifierar data, inte valet 5 %. Stryk påståendet att stor betald funding är nödvändig eller att marginalnivån bevisats irrelevant: även ett litet negativt C från funding kan med ett tillräckligt stort senare prisfall ge likvidation. Detta är en modellbegränsning, ingen sannolikhetsbedömning.

DSR är en diagnostik. 1 213 får beskrivas som det specificerade råa räknemåttet/känslighetsvärdet, men inte som verifierad fullständig historik över faktiskt körda oberoende försök: bland annat H-0016 och den nya hypotesen är ännu inte körda. Variansen från tio korrelerade kontrollkurvor är inte verifierad som variansen hos alla tidigare sökförsök. Undvik att kalla detta ett kalibrerat statistiskt intervall eller en bevisad konservativ yttergräns. N och t-krav för själva beslutet ska fortfarande låsas vid A2 från registret.

## Oberoende verifiering och omfattning

- Claudes `scripts/momentum-a1-oracles.py --check`: PASS. Detta reproducerar sparade räknetal; det verifierar inte en eventmotor eller undanröjer ovanstående kontraktsfel.
- Oberoende reproduktion: `python3 research/audits/momentum-a1-cb335ee/review.py --check`. Decimal-ledger för gap/funding, exakta syntetiska tider och ett Sharpe-motexempel. Resultat i samma katalogs `verification.json`.
- Befintliga tester: `cd engine && .venv/bin/python -m pytest tests/test_stats.py tests/test_registry_and_experiment.py tests/test_margin_reference.py tests/test_registered_export.py -q -p no:cacheprovider`: **29 godkända**.
- Alla fyra checklistgeneratorer kontrolleras med `--check`; `git diff --check` ska vara rent vid leverans.
- Inga råa marknadsarkiv eller prishistorik har lästs. Ingen ny registrering, strategikod, forskningskörning, SSH-ändring, migration, driftsättning eller publicering.

## Nästa leverans från Claude

Rätta enbart A1-utkastet, metodtabellen och de syntetiska oraklen för fynd 1–4 samt precisera modellbegränsningarna ovan. Bevara denna granskning som historik. Redovisa exakt ny commit/diffbas, ändrade regler och nya gränsfall. Behåll MOM-A03/MOM-A04 som in_progress och MOM-A05 som todo. **Ingen A2-registrering eller leverans B före Codex omgranskning av den nya revisionen.**
