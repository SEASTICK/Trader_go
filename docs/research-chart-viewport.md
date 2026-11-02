# Diagrammets synlighet och uppvärmning, 2026-11-02

Diagramkomponenten äger nu storleksändringen med ResizeObserver i stället för
bibliotekets autoSize. IntersectionObserver schemalägger en omritning på nästa
animationsruta när diagrammet blir synligt. Historikens första fitContent väntar
på synlig yta med positiv storlek. Återkomst och storleksändring återställer inte
användarens zoom. Observatörer och väntande animationsruta avregistreras innan
diagrammet tas bort.

Verifierat lokalt: 52 frontendtester inklusive dold/nollstor yta, återkomst utan
ny fitContent och avregistrering; TypeScript/Vite-bygge. Webbläsaren visar
verkliga historiska priser/markörer vid första framrullningen utan klick på
Hela perioden, i ljust och mörkt tema. Mac-runtime och Windows-runtime måste
redovisas separat efter att den nya appen provats.

Utforskningens UM-jobb använder januari 2020 som tidigaste månadsarkiv.
Tidigare kod begärde 2019 vid tidiga startdatum, vilket gav saknad fil. Kortare
uppvärmning än 600 staplar före perioden redovisas nu i varningar och metadata.
Ingen data fylls i och strategilogiken ändras inte. Ett komplett januari-test
med kontrollsummerade syntetiska arkiv kräver noll nedladdningar, inga affärer
innan EMA 200 är klar och identiskt resultat vid upprepning. Registrerade
originalresultat och strategiversioner är oförändrade.

Driftkontroll: worker och do-agent active, worker NRestarts=0, MemoryMax=2 GiB,
113 GiB ledigt. research.env 600, backupkatalog 700. Ingen serveromstart,
leverantörsåterställning eller larmleverans verifieras av denna kontroll.
