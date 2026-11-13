# Fryst känslighetskontroll av R001–R004 (efterhandsdiagnostik, utforskande)

Fråga (Codex efter #129): överlever de fyra kandidater som nådde slutsteget i R001–R004 den rättade urvalsbasen (396 USDT-perpar, `universe_at`, nuvarande täcknings- och kostnadsregler)?
Rapport: [frozen-r001-r004.md](frozen-r001-r004.md) (läsbar), `frozen-r001-r004.json` (alla tal). Kod: `engine/traderlab/agentlab/sensitivity.py`. Tester: `engine/tests/test_sensitivity.py`.

Reproducera (lokala rådata krävs, ca två minuter):

```bash
cd engine && .venv/bin/python -m traderlab.agentlab sensitivity
```

Regler för kontrollen
- **Ingen parameter ändras.** Specifikationerna läses ur `research/agentlab/experiments.jsonl` (stage `final`, run R001–R004, inga kontroller) och `make_spec(...)["key"]` måste vara lika med registrets nyckel, annars avbryts körningen. Fyra kandidater: X-0081 och X-0122 (`ensemble_rank`), X-0082 (`ml_xs`, lgbm) och X-0173 (`bab`).
- **Bara 2020-10-01..2022-12-31.** Panelen läses med `load_um_panel(end=2023-01-01)`: arkiv från 2023 och senare öppnas aldrig, och `evaluate` vägrar en panel som innehåller data efter 2022-12-31. Valid (2023), final (2024) och 2025+ är orörda.
- **Orört:** gamla registerposter, `state.json`, `research/registry.md`, R001–R004 och tidigare audits. Rapporten är efterhandsdiagnostik och inte en bekräftelse eller en ny hypotes (ingen registerrad).
- **Tre steg** gör avvikelsen förklarbar utan att regler justeras: A registrets gamla siffror, B samma 85 perpar med dagens regler (`r001-r004-panel-symbols.json` = de gamla panelens kolumnnamn), C hela panelen med dagens regler.
- **Mått:** universum, täckning/GILTIG–OGILTIG, nettoavkastning, Sharpe, t (`stats.t_stat` på dagliga nettoavkastningar), största nedgång, omsättning, finansiering och Sharpe med 2,5× kostnader. "Överlever" är en deskriptiv sammanfattning med trösklar som skrevs före körningen (`SURVIVE` i koden), inte ett beslutskriterium.
- **Urvalsfel:** de fyra är utvalda ur cirka 170 discovery-utvärderingar och trösklarna är inte justerade för antalet försök; "överlever" betyder bara att kanten inte försvinner av universumskorrigeringen.
