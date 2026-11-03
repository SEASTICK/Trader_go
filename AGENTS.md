# Arbete i TraderGO

Läs `CLAUDE.md` och relevanta projektinstruktioner före ändringar.

## Fas 2 / H-0013

- Läs `docs/fas2-checklista.md` och den gemensamma statuskällan `docs/fas2-status.json`.
- Efter varje relevant kodändring eller verifiering: uppdatera berörda uppgifter och underlag i samma leverans.
- Markera endast granskat och verifierat klart. Kod som bara finns eller är pushad är inte automatiskt klar.
- Sänk status till `in_progress`/`todo` när en ändring ogiltigförklarar tidigare verifiering.
- Kör `python3 scripts/render-fas2-checklist.py` och därefter samma kommando med `--check`.
- När checklistan visas i chatten: regenerera vyn från statuskällan. Påstå inte att chatvyn följer andra sessioner i bakgrunden.
- Skilj H-0013 från tvärsnitt H-0014/H-0015 samt lokal kod från driftsättning och Stable.
- Ändra inte frysta forskningsprotokoll, resultat eller REJECT-beslut för checklistans skull.

## Fas 3 / Live Paper Trading

- Följ docs/fas3-status.json och docs/fas3-checklista.md efter varje relevant ändring eller verifiering. Markera bara granskat och verifierat arbete klart, med underlag.
- Regenerera med `python3 scripts/render-fas3-checklist.py` och kontrollera med `--check`. Chatvyn är en ögonblicksbild.
- Skilj tekniska SIM-prov från fryst framåttest. Pilot kräver READY_FOR_PAPER, fryst strategi och dokumenterat startbeslut; H-0013 förblir REJECT.
- Skilj implementation, driftsättning, pågående observationsperiod och slutgodkännande. Ingen automatisk liveövergång.

## H-0016

- Följ docs/h0016-status.json och docs/h0016-checklista.md efter relevanta ändringar eller verifieringar; bocka bara av granskat och verifierat arbete med underlag.
- Regenerera med `python3 scripts/render-h0016-checklist.py` och kontrollera med `--check`. Chatvyn är en ögonblicksbild.
- Förregistrerade regler i research/h0016-protokoll.md ändras inte för att rädda ett resultat. Skilj dokumenterat kontrakt från implementation, körning och resultat. H-0013 förblir REJECT.
