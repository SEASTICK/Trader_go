# Research Lab H-0013 – granskning av PR #77

Granskad PR-head: `f36a3eea9bb1fd887aa02a50ebccc5a4d6f97c93`, kod `62cc4bb`, gren `fas2-research-lab`. PR: https://github.com/SEASTICK/Trader_go/pull/77. Granskning 2026-11-03. PR #76 är mergad som `d1e32ed` med senaste verifierade driftstatus.

Bara isolerad PR-kopia, syntetiska payloads och lokal webbläsarvy med stubbat API har använts. Ingen riktig inloggning, Supabase-köning, H-0013-körning, serverändring, slutprovsläsning eller publicering gjordes.

## Fynd före merge

### P2 – platta kapitalkurvor och noll-drawdown blir tomma diagram

`app/src/features/research-engine/H0013Panel.tsx:172–174` skickar konstant kapital och konstant drawdown till den gemensamma `LineChart`. Dess befintliga skalning i `app/src/components/Charts.tsx:31–39` får hi=lo när alla värden är lika och dividerar med noll. Det nya flödet behöver stödja en platt H-0013-spelbok: det är ett tillåtet och tidigare syntetiskt observerat urvalsutfall.

Oberoende prov i riktig Chrome med syntetisk equity `[1,1,1]`: både kapital- och drawdown-diagram saknar linje. DOM innehåller bland annat `M8.0,NaNL769.0,NaNL1530.0,NaN`. Felet bekräftades visuellt i både ljust och mörkt tema. Även en jämnt stigande equity kan ge en helt konstant drawdown-kurva på noll.

Hantera konstant domän i den återanvända grafen eller med en gemensam säker grafadapter. Visa horisontell kapital-/nollinje med ändliga koordinater; dölj inte ett giltigt platt resultat. Lägg regressioner för konstant positiv equity, noll-drawdown och vanlig varierande kurva, och kontrollera faktisk SVG/visning utan NaN/Infinity. Kontrollera övriga grafanvändare om den gemensamma komponenten ändras.

### P2 – ett tillfälligt fel i resultathämtningen fastnar och felmeddelandet försvinner

`app/src/features/research-engine/H0013Panel.tsx:32–39` hämtar payload bara när de uttryckliga effektberoendena ändras. Ett misslyckat anrop ändrar bara error. Nästa lyckade körningspoll på rad 25 rensar dessutom samma error, utan att trigga en ny payloadhämtning när id/status är oförändrade. Vyn ligger därför kvar på Hämtar resultat utan möjlighet att försöka igen.

Oberoende interaktivt prov: stubbat API ger en done-körning; första payload-anropet kastar ett tillfälligt anslutningsfel och varje senare anrop skulle lyckas. Efter **10 körningspollningar finns bara 1 payload-anrop**, feltexten är borta och Hämtar resultat visas fortfarande. Ingen verklig server kontaktades.

Skilj list-/payloadfel och laddningsstatus åt. Ge en fungerande återförsöksväg, automatiskt eller genom en tydlig knapp, och behåll payloadfelet tills det hanterats. En lyckad listpoll får inte dölja ett olöst resultatfel. Lägg ett riktigt komponent-/webbläsartest med effekter: första resultatanropet misslyckas, nästa lyckas, resultatet visas och inget köanrop görs. Kontrollera också byte av vald körning och utloggning medan ett anrop pågår.

### P2 – saknad affärslista presenteras som noll affärer

`app/src/features/research-engine/h0013.ts:168` gör saknad, feltypad eller helt bortfiltrerad trades till `[]`. `H0013Panel.tsx:185` visar då Senaste 100 av 0 och Inga affärer i resultatet, trots att antalet är okänt. Listan tas inte heller upp som saknad i missing.

Oberoende renderat prov med stats.trades=4 och utan trades-fält: sammanfattningen visar 4 affärer, men affärsdelen visar 0 och Inga affärer. Detta bryter kravet att saknade delar ska visas som saknade och kan dölja att affärsloggen inte har levererats.

Skilj en verifierad tom lista från saknad eller ogiltig lista. Visa Affärsloggen saknas när den inte kan läsas och redovisa avvikelse mot ett rapporterat antal. Filtrera inte bort trasiga rader utan att redovisa ofullständigheten. Lägg tester för saknat fält, fel typ, blandat giltiga/ogiltiga rader och en faktiskt tom lista med rapporterat antal 0. Fyll inte i påhittade affärer eller nollvärden.

## Verifierat

- **85 frontendtestfall passerar**, inklusive 27 nya H-0013-testfall. Första körningen fick en EPERM vid skrivning till delad cache efter passerade tester; körningen upprepades med cache avstängd och avslutades med exit 0. **Produktionsbygget lyckas.** Vites storleksvarning för ett befintligt stort paket kvarstår, inte ett testfel. CI App check är grön på exakt PR-head.
- Låst protokoll matchar migration, motor, worker och register i testerna. Ny flik skiljer H-0013 från Fas 1, tvärsnitt och utforskning; befintlig inloggning och API återanvänds.
- Förberedelsen använder samma enda fasta kökontrakt, bekräftelse före anrop och blockerare för aktiv/färdig körning. Köanropets kropp innehåller bara request_key; databasens egna spärrar gäller fortsatt. Ingen köning utfördes i granskningen.
- Resultatläsningen avvisar fel hypotes, version, dataset, ofullständig status, booleskt fel slutprovsskydd, simulerat flaggat resultat samt inkonsekvent kriterie-/beslutsobjekt. De flesta saknade delar redovisas; affärslistan är undantaget i fyndet ovan.
- Syntetisk resultatvy granskades i Chrome på Mac i ljust och mörkt tema, med återanvända komponenter/CSS. API:t var helt stubbat och köning avstängd. Det är inte ett verifierat inloggat Supabase-flöde eller en installerad Mac-/Windows-app.
- Jämförelsernas nyckeltal finns, men deras kurvor finns inte i nuvarande resultatpayload. Vyn redovisar begränsningen. **F2-704 kan därför inte räknas som helt klar**, även efter rättat platt diagram, förrän jämförelsekurvorna har levererats/visats eller uppgiftens avgränsning uttryckligen ändrats. Ändra inte frysta resultat för att fylla luckan.

## Checklista och beslut

F2-701 och F2-702 är lokalt kodmässigt verifierade. F2-703 lämnas in_progress för felåterhämtningen, F2-704 för grafen och jämförelsekurvorna, F2-705 för korrekt hantering av saknad affärslogg. Gemensam status: **32/40 verifierade**.

**PR #77 är inte godkänd för merge ännu.** Nästa kontroll är rättade tre fynd med interaktiva och renderade regressioner, fortsatt bara syntetiska data. Ingen riktig H-0013-körning ska startas för att testa vyn. Inga strategiresultat är godkända för papper/live.
