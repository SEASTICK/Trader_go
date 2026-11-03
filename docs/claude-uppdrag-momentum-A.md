# Claude – leverans A: metodkontrakt och förregistrering

Du implementerar TraderGO under Codex granskning. Edwin har bett att Codex börjar med metodkontrollen. Den kontrollen finns nu som ett underlag, inte ett godkännande att köra forskning eller ändra servern.

## Utgångsläge

- Läs AGENTS.md, CLAUDE.md och docs/h0013-efterfoljare-forskningsplan-20261103.md.
- Läs docs/momentum-metodgranskning-20261103.md och docs/momentum-implementationskontrakt-utkast.md i sin helhet.
- Läs docs/momentum-status.json och docs/momentum-checklista.md.
- H-0013 REJECT bevaras. H-0016 är en separat förregistrerad, oprövad squeeze och får inte skrivas om.
- Origin/main var 72107ed vid Codex kontroll. Forskningsplanen ligger på f43c1e7 och är inte mergad dit. Utgå från den branch/commit som innehåller denna handoff och redovisa aktuell diffbas; börja inte från en äldre main som saknar protokoll och statusfiler.
- Kolla arbetskopia/HEAD/dirty/fjärrgrenar innan ändringar. Bevara andra sessioners arbete; ingen force-push/reset.

## Din enda leverans nu

Färdigställ ett exakt förregistreringsbart kontrakt för den enda momentummodellen. Använd Codex utkast som föreslagen semantik, men påstå inte att utkastet redan är godkänt. Avvikelser från forskningsplanen eller utkastet ska stå i en metodtabell med skäl före implementation och resultat.

Lös samtliga M01–M08. Särskilt återstår:
1. Låst huvud- och känslighetsordning för funding/handel och en förutbestämd klassificeringsregel om de ger olika godkännanden.
2. Historiskt motiverad eller uttryckligen avgränsad marginal-/likvidationsmodell, mark-price-krav och publicerbara källor. Gissa inte historiska regler från dagens kontoinställningar. Inga börsnycklar behövs eller får efterfrågas.
3. Exakt konservativ intrastapel-bound även för legacy-kontroller med ATR-stop.
4. Fullständiga vikt-, avrundnings- och partial fill-regler för alla kontroller. Bevara legacy-signalernas egna riktningar/stop, utan att tyst lägga huvudmodellens nya riskstopp på dem.
5. Exakt DSR-/försöksredovisning, inklusive beroende och tidigare sökningar. Kopiera inte bara N från gamla H-0013.
6. Handräknade exempel enligt K09, inte bara allmän text om att tester ska skrivas senare.

Dela A i två kontrollerbara steg. **A1:** lämna först komplett kontrakt/protokollutkast, metodtabell och orakel för Codex granskning, utan att lägga en registerrad. **A2:** först efter Codex godkännande av exakt A1-revision, skapa det slutliga protokollet och registreringscommiten. Kontrollera då ledigt id i senaste gemensamma registret; 16 id fanns vid Codex kontroll och H-0017 är inte reserverat. Lägg endast till registreringen sist och committa före historik, enligt ny-hypotes. Koppla protokoll och status till exakt id/revision. Ändra aldrig tidigare registerrader. Förregistrera inte ett protokoll som fortfarande har öppna materiella modellval.

Tillåtna filer i A1/A2: nya metod-/protokoll-/granskningsdokument, ny registerrad när kontraktet är fullständigt, nya specifikationsfixturer/orakel utan inläsning av marknadshistorik samt berörda status-/genererade checklistfiler. Relevanta befintliga register-/exportkontroller får köras.

## Inte i denna leverans

Ingen signal-/riskimplementation i engine eller app, ingen marknadshistorik eller skyddade 2025-arkiv, inga nya forskningsresultat, ingen migration, SSH-mutation, workerstart/-stopp, driftsättning, PR-merge eller release. Ingen automatiskt startad paper/live. Inga gamla protokoll eller REJECT-beslut ändras.

Kan en metodfråga inte lösas utan en ny övergripande avgränsning, redovisa den konkret till Codex och lämna berörd punkt öppen. Gå inte runt blockeraren med en tyst förenkling.

## Rapport tillbaka

Lämna gren, HEAD, diffbas, ändrade filer, register-id/N/t-krav om registrerat, eventordning, jämförelsematris, handräknade kontrollfall, körda verifieringar och kvarstående begränsningar. Ange vad som faktiskt är verifierat och vad som bara är specificerat.

Uppdatera docs/momentum-status.json med underlag. Behåll nya A-punkter in_progress tills Codex granskat dem. Kör python3 scripts/render-momentum-checklist.py och --check. Leverans B börjar först efter Codex godkännande av exakt A-revision.
