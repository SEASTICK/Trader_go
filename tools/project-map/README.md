# Project map

An Obsidian Canvas that shows how TraderGO's files and notes connect. It updates by itself.
A small local watcher indexes the repo, so routine updates need no Claude, no LLM, no network
and no paid API. The tool only reads project files. It writes to two places only: the output
folder in the vault and its own state folder. It has no trading, broker or key code.

Requires Node 20 or newer (the app already needs it). Git is optional, but with Git the tool
follows `.gitignore` exactly.

## What you get

All of this is in `research/TraderGO/00 Dashboard/Project Map/` (open `research/` as the vault):

| File | What it is |
|---|---|
| `Project Map.canvas` | The overview: one group per area, plus **Unconnected / To review** |
| `Project Map – <area>.canvas` | Detail canvas for an area with more than 18 files. The overview shows the most connected files and a card that links here. |
| `Project Map Index.md` | Every indexed file, grouped, with links. Also lists unresolved links. |

- **Vault files** (anything under `research/`) are real file nodes. Click to open, double-click to preview.
- **Files outside the vault** (skills, app, CI) cannot be file nodes in Obsidian. They are cards
  whose title is a `file://` link, which opens the file in your default app.
- **Lines:** purple = explicit link (`[[wikilink]]`, `![[embed]]`, Markdown link, canvas file
  node). Green = verified dependency, meaning the target resolved by language rules: JS/TS
  `import`, Rust `mod`/`include_bytes!`, Python `import`, HTML `src`, CSS `@import`, or a path
  string in JSON, YAML or TOML config. Grey with `≈` = inferred: a path or skill name in
  backticks, such as `` `research/registry.md` `` or `` `pengar-grind` ``.
- Files with no connection at all go into **Unconnected / To review**.
- Attachments (images, PDFs, binaries) are listed as file nodes but never parsed.

## How sync works

1. At startup, the watcher reconciles the whole index: it lists files with
   `git ls-files --cached --others --exclude-standard`, applies the exclude patterns, and
   re-parses only the files whose size or modification time changed.
2. Then it listens for file events in the whole repo (Node `fs.watch`, FSEvents on macOS).
   Events wait for 1.5 s of quiet. The watcher then checks that the changed files have stopped
   growing and that no Git operation is running (`.git/index.lock`). Then it runs one full
   reconcile. Git pulls, checkouts and sync tools are covered because they change files on disk.
3. Every reconcile rebuilds the graph from scratch, so renamed and deleted files never leave
   stale nodes or lines behind. A rename is detected by identical content, and the node keeps
   its position.
4. Canvases are written atomically (temp file plus rename), and only when the content changed.
   The output and state folders are excluded from the index and ignored by the watcher, so the
   tool's own writes never trigger another run.
5. A full reconcile also runs every 10 minutes, as a safety net for missed events.

### Your layout is kept

- Move or resize any generated card or group in Obsidian. On the next update, the tool sees
  that it differs from what it wrote last time, pins it there, and keeps it. A changed card
  colour is kept too.
- Cards and lines you add yourself (text, links, your own arrows) are kept as they are. A line
  you drew to a file that is later deleted is removed with it.
- New files take the next free slot in their group, so existing cards never shuffle.
- Generated cards are rewritten on every update. Don't edit their text; add your own card instead.
- Layout state lives in `tools/project-map/.state/layout.json`.
- Generated files and state are in `.gitignore`. Each of you has your own map and layout, and
  nothing generated ever causes a merge conflict.

## Start and stop

From the repo root:

```bash
node tools/project-map/project-map.mjs start     # watcher in the background
node tools/project-map/project-map.mjs status    # running? last log lines
node tools/project-map/project-map.mjs stop
node tools/project-map/project-map.mjs watch     # in the foreground (Ctrl+C stops it)
```

The log is `tools/project-map/.state/watcher.log`.

### Manual refresh and rebuild

```bash
node tools/project-map/project-map.mjs refresh                 # one full reconcile now
node tools/project-map/project-map.mjs rebuild                 # drop the parse cache, re-read every file
node tools/project-map/project-map.mjs rebuild --reset-layout  # also forget all positions (your own cards stay)
node tools/project-map/project-map.mjs check                   # validate: JSON, ids, edges, every file present
```

A refresh is safe while the watcher runs, because a lock file serialises them.

### Start at login (macOS, optional)

```bash
node tools/project-map/project-map.mjs install-agent    # writes ~/Library/LaunchAgents/com.tradergo.project-map.plist and starts it
node tools/project-map/project-map.mjs uninstall-agent
```

The agent runs `watch` with the `node` you installed it with, restarts it after a crash, and
logs to the same file. The repo is under `~/Documents`, so macOS may ask whether `node` may
access the Documents folder. If the log shows `EPERM`, allow it in System Settings → Privacy &
Security → Files and Folders. On Windows, run `start` by hand or add it to Task Scheduler.

## What is monitored, and how to change it

Settings are in `tools/project-map/config.json`. For personal changes, create
`tools/project-map/config.local.json`. It is git-ignored, and its keys override the shared
file. `exclude_add` and `include_add` append to the lists instead of replacing them.

- **Monitored:** the whole repo (`"include": ["**"]`), with the vault at `research/`.
- **Always skipped:** everything in `.gitignore`, plus `exclude`: `.git/`, `.obsidian/`,
  `node_modules/`, `target/`, `dist/`, `gen/`, `build/`, `.env*`, keys and certificates
  (`*.pem`, `*.key`, `id_rsa*` …), caches, `data/raw/`, `data/clean/`, `.DS_Store`, temp and
  swap files. The output and state folders are always excluded.
- **Not parsed** (listed only): `no_parse` (lock files) and every file type without a parser.

Patterns follow `.gitignore` rules. `dir/` matches a folder anywhere, a pattern with a `/` is
anchored at the repo root, `**` crosses folders, and `!pattern` re-includes. For example, to
hide the third-party skills' licence files and add a folder of your own:

```json
{ "exclude_add": ["LICENSE.upstream", "scratch/"] }
```

Other settings:

- `groups`: the areas, matched top to bottom (first match wins). `split` makes one group per
  subfolder, as for the vault folders.
- `aliases`: names that count as an inferred link when written in backticks (skill names by default).
- `overview_max_per_group`: when an area gets its own detail canvas.
- `layout`: card size and spacing.
- `debounce_ms`, `settle_ms`, `reconcile_minutes`: watcher timing.

After changing the config, run `refresh`. The cache resets by itself when the config changes.

## Limits

- Links are found with regular expressions, not full parsers. A link spelled in an unusual
  way can be missed, and a path string in config can be over-counted. Unresolved explicit
  links are listed in the index.
- File events cover the repo folder only, and the vault must be inside it.
- Inside Obsidian there is no refresh button. Run `refresh`, or just save any file.
