# Codex godkännande av H-0017:s A2-registrering

Datum: 2026-11-03. Granskad revision och registreringscommit: **`db7f83b56e79f8a76b5e0d297be4503170070c0f`**. Diffbas: `0cbc32b`.

**A2 godkänns. Leverans A är klar och leverans B får påbörjas enligt den separata B-instruktionen.** Inga blockerande fynd. Detta är ett godkännande av förregistrering och metodproveniens, inte en verifierad implementation, datakvalitet eller ekonomisk strategi.

## Oberoende verifierat

- Lokal arbetskopia var ren på `claude/momentum-a1`, HEAD=db7f83b. Fjärrgrenen verifierades med `git ls-remote` på samma fullständiga hash. Fjärr-main är fortsatt `72107ed`; använd hela registreringskedjan inför B.
- Diffen omfattar endast nytt slutprotokoll, en tillagd registerrad och momentumstatus/checklista. Ingen engine-, app-, migrations- eller driftkod ändrad.
- Registret efter A2 börjar med **exakt hela** registret före A2 och har en enda ny rad sist, H-0017, med 13 kolumner. Alla tidigare registreringar/resultat/REJECT-beslut är därmed byte-identiska.
- I registreringscommitens föräldrakedja fanns 16 distinkta id och inget H-0017. En läsande kontroll av 116 lokala/fjärrreferenser vid granskningen fann ingen konkurrerande H-0017-rad; de två referenser som innehöll id:t hade samma rad. Detta återger granskningsläget, inte ett lås för framtida id.
- `registry.require_registered('H-0017', repo)` accepterar den committade registreringen och ger registreringscommit db7f83b, **N=17**. Kravet är **2,754268270633685**. Låst **N_sok=1 213**, som specificerat rått diagnostiskt räknemått.
- Slutprotokollets §1–§18 är identiska med godkända A1 a25db81 efter den deklarerade mekaniska länkanpassningen. Alla 11 lokala länkar i slutprotokollet finns. Identitetsblocket anger id, version, källrevision och kontrollsummor. De godkända A1-filerna matchar SHA-256 från tidigare oberoende verifiering.
- De tre äldre granskningsdokumenten och deras auditfiler är bevarade. Ingen materiell metodändring har smugit in i A2.

Reproducerbar kontroll: `engine/.venv/bin/python research/audits/momentum-a2-db7f83b/review.py --check`. Den sparade `verification.json` innehåller kontrollsummor för slutprotokollet och registret. Skriptet läser dokument och Git-historik, inte marknadshistorik.

## Tester och avgränsningar

- **36 tester godkända:** stats, registry/experiment, margin reference, registered export och tracks, körda med `engine/.venv/bin/python -m pytest` från engine, `-q -p no:cacheprovider`.
- A1-oraklen samt alla tre tidigare granskningsskript passerar med projektets venv. Den nya A2-kontrollen passerar också.
- Alla fyra checklistgeneratorer med `--check`: PASS. `git diff --check 0cbc32b db7f83b`: rent.
- Sparade flyttalsresultat i tidigare audits kontrolleras i projektets venv; de är inte ett löfte om bitidentiska statistikresultat över olika numpy-/Pythonmiljöer. Inga gamla verifieringsfiler har ändrats för att passa en ny miljö.

MOM-A05 markeras klar. Hela grupp A är därmed 5/5 och checklistan **5/40**. Alla B-punkter väntar på implementation och granskning. Statuskällan kopplas nu uttryckligen till H-0017.

Kvarstående begränsningar består: ingen marknadshistorik läst i denna granskning, ingen verklig datakvalitetskontroll, fundingtidsaudit, motor eller ekonomiskt resultat för H-0017. Börsmodellens antaganden, redan sedd utvecklingsperiod och DSR:s diagnostiska roll är oförändrade. H-0013 förblir REJECT, H-0016 är separat, ingen kandidat är godkänd för paper/live. Tidigare Windows-/Gatekeeper-/larm-/temabegränsningar är inte omprövade här.

## Nästa steg

Claude följer [leverans B](claude-uppdrag-momentum-B.md): ren signalmodul, bara syntetiska tester och inget konto-/utförandelager. Slutprotokoll och registreringsrad ska förbli oförändrade. Nästa beroende leverans väntar på Codex granskning av exakt B-revision.
