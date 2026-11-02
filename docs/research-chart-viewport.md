# Historikdiagram och uppvärmning, 2026-11-02

Endast historikdiagram använder en egen ResizeObserver och IntersectionObserver.
Storlek och första fitContent väntar på en synlig yta med positiv storlek och
schemaläggs på nästa animationsruta. Återkomst och storleksändring begär ingen
ny fitContent, så användarens zoom behålls. Observatörer och väntande
animationsruta avregistreras innan diagrammet tas bort.

Historikens minsta stapelbredd är 0,01 pixlar så att alla 6 576 staplar ryms.
Marknadsdiagram behåller bibliotekets ursprungliga autoSize och gräns 0,5 pixlar.
Strategier, ursprungliga forskningsresultat och appens uppdaterare ändras inte.

Verifierat lokalt: 52 frontendtester inklusive dold/nollstor yta, återkomst utan
ny fitContent och avregistrering; TypeScript/Vite-bygge. Webbläsaren visar hela
2022–2024 och affärsmarkörer vid första framrullningen utan klick på Hela
perioden, i ljust och mörkt tema. Mac-paketet 0.1.15 visade första ritningen
innan den sista avgränsningen och stapelbreddsfixen; slutpaketet redovisas i
leveransrapporten. Windows-runtime saknar testdator enligt användaren.

En tom canvas i Marknad observerades både i kontrollpaket 0.1.15 och installerad
Stable 0.1.14 trots uppdaterad OHLC-rad. Fönstrets Raise löste inte detta.
Rotorsaken är inte fastställd och detta är inget godkänt regressionstest.
Den nya storlekshanteringen begränsas till historik för att hålla ändringen
avgränsad. 0.1.15 och 0.1.16 stoppades före publicering.

## Tidig terminsuppvärmning

Utforskningens UM-jobb använder januari 2020 som tidigaste månadsarkiv.
Tidigare kod begärde 2019 vid tidiga startdatum, vilket gav saknad fil. Kortare
uppvärmning än 600 staplar före perioden redovisas nu i varningar och metadata.
Ingen data fylls i och strategilogiken ändras inte. Ett komplett januari-test
med kontrollsummerade syntetiska arkiv kräver noll nedladdningar, inga affärer
innan EMA 200 är klar och identiskt resultat vid upprepning.

Servern kör källversion 4d2ba56; senare desktopcommits ändrar ingen Python-kod.
Alla 145 Python-tester passerar på Mac och Ubuntu. Riktig Binance-historik för
januari 2020 verifieras med två arkiv, 93 fundinghändelser (högst 2 ms fördröjning),
noll affärer före EMA-uppvärmning och två byte-identiska resultat. Rapport:
`data/audits/fas1-20261102/warmup-verification.json`. Inget slutprov eller nytt
strategiurval ingår.

Driftkontroll efter aktivering: worker active/running, NRestarts=0, MemoryMax=2 GiB,
113 GiB ledigt; do-agent active. research.env 600, backupkatalog 700 och tidigare
backupfil finns kvar. Tom kö kontrollerades före och efter stopp, tidigare
källversion behölls och återgång vid startfel fanns i aktiveringsskriptet.
Ingen serveromstart, leverantörsåterställning eller larmleverans verifieras av
denna kontroll.

## Publicerad leverans

Stable 0.1.17 publicerades från 153e422 via körning 41439841229, alla jobb
godkända. Plattformarnas CI visar vardera 52/52 tester och lyckade byggen.
Mac- och Windows-paketens minisign-signaturer verifierades; ändrade paket
avvisades. Mac codesign, program-id och universalformat kontrollerades.
Samtliga sex offentliga feed-alias pekar på kontrollerade filer och signaturer.
Rapport: `data/audits/fas1-20261102/stable-chart-verification.json`.

Det manuella Mac-testet av slutpaketet och installerad uppdatering är fortfarande
öppet: appverktyget gav först timeout, sedan timeout även efter återanslutning
och återställd verktygssession. Detta bevisar inte att själva appen har hängt.
Installerad version senast kontrollerad är 0.1.14. Ingen Windows-dator finns
tillgänglig för manuellt test. Fas 1 är inte slutgodkänd.

Efter publiceringen tillkom PR #59 och #61 på main (5d6c8ff). De ingår inte
i ovanstående paket eller testbelägg. Deras server-deploy körning 41441143904
hoppade över driftsättning (SERVER_HOST saknas); kontroll av systemd visade
endast den redan verifierade research-workern aktiv. Ingen ny deploy eller
extra worker startades av denna leverans.
