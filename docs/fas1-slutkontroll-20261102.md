# Fas 1 – slutkontroll 2026-11-02

Omfattning: historisk BTC/USDT-forskning vid 1×. Inga riktiga order, ingen godkänd strategi för framåttest. Windows manuella app-test och driftlarm är uttryckligen uppskjutna av Edwin. Publicering och installerad Stable kontrolleras separat efter bygget.

- [x] Två senare integrationer granskade och samordnade. En kanonisk worker; gamla tjänsten maskerad och alternativa driftsättningar stoppade. Se `research-integration-review.md`.
- [x] Marknadsdiagrammet rättat: storlek och första visningsområde sätts efter verklig layout. Resize/start får inte invänta en första IntersectionObserver-notis från WebKit. Native Mac-test av första visning, sidbyte, omstart och storleksändring; separat från webbläsarprovet.
- [x] Automatisk inkrementell synk på dropleten, var femte minut och vid uppstart. Sex serier: spot/UM, 1h/4h/1d, plus funding. Upprepade verkliga körningar och omstart av tjänsten passerade. Pågående staplar hålls åtskilda; stängda värden skrivs inte över.
- [x] Synken samlar framåt från 2026-11-02 UTC. Den fyller inte den skyddade perioden 2025–2026. Detta är två avgränsade dataset, inte obruten historik fram till idag. De frysta 10 962 staplarna och 5 481 fundingraderna har exakt samma SHA efter synken.
- [x] Registrerad reproduktion från Research Lab: H-0009 köad genom verklig inloggad UI, sparat serverresultat, exakta ursprungliga nyckeltal/kurvor och REJECT. H-0010–H-0012 reproducerade genom samma medlems-RPC i blandad kö. Ingen ny optimering eller läsning av slutprovet.
- [x] Samtidiga reservationer ger en ägare; högst en aktiv körning observerades. Dubbla förfrågningar återger samma jobb. Köat avbrott före start och aktivt avbrott på 9,408 sekunder; inget resultat från avbruten körning. Ogiltiga parametrar ger sparat misslyckande. Alla försök behålls.
- [x] Återtagning efter utgången reservation, avvisning av gammal token och faktisk workeromstart verifierades i föregående molnprov (`research-cloud-verification.json`); reservationsfunktionerna är oförändrade. Nya kontraktet och båda jobbtyperna provas även isolerat mot migration 0004.
- [x] Mark-price- och marginalkontroll för de fyra frysta 1×-körningarna. 60 månadsarkiv plus åtta dagsarkiv, alla med officiella kontrollsummor. 48 luckor i månadsarkiven återhämtades enligt förregistrerat tillägg, utan imputation. Samtliga 267 affärer kontrollerade, inga möjliga likvidationsträffar vid 0,5–1 % underhållsmarginal. Minsta marginal/notional 74,64 %.
- [x] Varje resultat spåras till ursprungsfil, parametrar, dataset, kodfingeravtryck och körnings-id. Mark-price-rapporten är separat; ursprungliga REJECT-beslut och testresultat ändras inte.
- [x] Isolerad återställning från ny privat export: alla typade värden identiska, RLS passerad, migrationerna 0001–0004 använda. 11 954 candles, 5 483 fundingrader, fyra strategier, tolv hypoteser, tolv jobb, sju resultat och 274 affärsrader. Exporten ligger utanför Git; tillfällig teståtkomst borttagen.
- [x] Belastningsprov med blandad kö: 49,177 sekunder totalt inklusive aktivt avbrott, cirka 104 MiB uppmätt toppminne i workertjänsten. CPU-kvot 150 %, minnestak 2 GiB. Detta är ett litet faktiskt köprov, inte ett kapacitetslöfte.
- [x] Manuella driftkontroller och återställningsrutin dokumenterade. Leverantörsbackuper enligt användarens bekräftelse; inga nya betaltjänster eller driftlarm.
- [x] Python: 176 tester. Frontend: 62 tester (inklusive de sju nya animationstesterna) och produktionsbygge. Rust: 48 passerade, ett avsiktligt nätverkstest överhoppat. Isolerade kö-/RLS-/leasekontroller passerade.
- [ ] Stable-publicering och kontroll av installerad version efter publicering.
- [ ] Windows manuellt app-test: uppskjutet enligt beslut.
- [ ] Driftlarm: uppskjutna enligt beslut.

## Avgränsningar som består

Den äldre motorns likvidationsformel är en approximation. Oberoende mark-price-kontrollen gäller de frysta körningarna vid 1×, inte historiska Binance-risktrappor, likvidationsavgifter eller godkännande för högre hävstång. Originalmotorn ändrades inte för att förbättra frysta resultat.

Spotluckan 2020-02-19 kvarstår och fylls inte med påhittade staplar. De tidigare rapporterade 43 feljusterade staplarna från 2017 kunde inte återskapas utan originalmaterialet. Den verifierade femårshistoriken för Fas 1 är UM BTCUSDT 4h. Full leverantörsåterställning av Supabase Auth/Storage och en hel droplet har inte genomförts; det godkända provet är en isolerad återställning av forskningsdatabasen.

Alla fyra Fas 1-strategier är REJECT. Ingen går automatiskt vidare till Fas 2 eller fryst papperstest. Historiska resultat är inga prognoser.

## Bevis

`data/audits/fas1-20261102/`:

- `mixed-queue-verification.json`: riktiga kö-, avbrotts-, parameter- och samtidighetsprov.
- `forward-sync-frozen-verification.json`: frysta SHA och sex synkade serier utan dubbletter.
- `final-restore-verification.json`: ny isolerad återställning, typade värden och RLS.
- `mark-price/verification.json`: komplett mark-price- och marginalkontroll.
- `mark-price/failed-coverage-verification.json` och `recovery-manifest.json`: första misslyckandet och spårbar återhämtning.
