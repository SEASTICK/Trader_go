# Conventions for TraderGO notes

Load this only when creating or restructuring notes.

## Folders (inside `research/TraderGO/`)

| Folder | Holds | Template |
|---|---|---|
| `00 Dashboard/` | Index notes and Bases views. One canonical index per area. | none |
| `01 Research/` | Hypothesis notes, loose ideas, reading notes, market observations | `forskningslogg` (hypotheses) |
| `02 Strategies/` | One note per strategy | `strategy-research.md` |
| `03 Backtests/` | One note per backtest run that matters | `backtest-summary.md` |
| `04 Architecture/` | One note per decision (ADR) | `architecture-decision.md` |
| `05 Paper Trading/` | One note per trade or per day | `paper-trade.md` |
| `06 Risk/` | Risk limits, incident notes, post-mortems | none |
| `07 Data Sources/` | One note per source: what, where, licence, known gaps | none |
| `08 Meetings and Decisions/` | Short notes from the two of you deciding things | none |
| `09 Archive/` | Retired notes. Move here only with approval. | none |
| `Attachments/` | Images and PDFs referenced from notes | none |

The skill's templates are the master copy. `Templates/` in the vault, if created, holds copies
for using in Obsidian by hand.

## Filenames

- Strategy: `S-<short name>.md`, e.g. `S-funding-carry.md`. A new version is a new note
  (`S-funding-carry v2.md`), because a changed strategy is a new strategy.
- Backtest: `BT-YYYY-MM-DD <strategy> <version>.md`
- Architecture: `ADR-0001 <short title>.md` (number = next free)
- Paper trade: `PT-YYYY-MM-DD <symbol>.md`
- Hypothesis IDs (`H-0001`) come from `research/registry.md` and are reused, never invented.

## Frontmatter

- Dates: `YYYY-MM-DD`. Set `created` once; set `updated` on every edit you make.
- `status` values. Strategy: `idea | testing | paper | rejected | retired`.
  Backtest: `draft | reviewed`. ADR: `proposed | accepted | superseded | rejected`.
- `tags`: lowercase, no `#` in frontmatter. Always include the note type
  (`strategy`, `backtest`, `adr`, `paper-trade`).
- Empty fields stay empty. Never fill a number you don't have.

## Labelling claims

Mark what kind of statement it is, so a guess never reads like a result:

```markdown
> [!fact] Binance perpetual funding is settled every 8 h.
> [!assumption] Slippage of 2 bp per side at our size.
> [!finding] Out-of-sample Sharpe 0.4 over 2023 (see [[BT-2026-11-02 funding-carry v1]]).
> [!hypothesis] Funding extremes mean-revert within 3 days.
```

Backtest numbers are history, never a forecast.

## Links

- Link with `[[note name]]`. Link to repo files with a relative Markdown link from the note,
  e.g. `[report](../../../reports/bt-2026-11-02.html)`, or give the repo path in backticks.
- Every strategy links its backtests; every backtest links its strategy and registry ID.
- Big results (trade lists, equity curves, parameter grids) stay in repo files. The note gets
  the headline numbers and a link.

## Searching cheaply

```text
Glob   research/TraderGO/**/S-*.md               # by filename
Grep   "^#+ .*funding"   path=research/TraderGO  # by heading
Grep   "tags:.*backtest" path=research/TraderGO  # by tag
Grep   "\[\[S-funding-carry" path=research/TraderGO  # backlinks to a note
```

Use `output_mode: files_with_matches` first, then read only the lines you need.
