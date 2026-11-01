# TraderGO

Två personers tradingforskning: bara historik och papper, aldrig riktiga pengar. Regler för
arbetet finns i [CLAUDE.md](CLAUDE.md).

## Mappar

| Mapp | Vad |
|---|---|
| `app/` | **Trader_go**, skrivbordsappen för forskning och papperstrading (Tauri + React). Inga mäklarkopplingar, ingen orderkod. Se [app/README.md](app/README.md). |
| `apps/trader-go-universe/` | **TraderGO Universe**, en karta över hela projektet som bara läser (Tauri + React Flow). Se [docs/universe.md](docs/universe.md). |
| `engine/` | Forskningsmotorn: data, backtest, statistik, registret. |
| `research/` | Registret, experimenten och resultaten. Också Obsidian-valvet (`research/TraderGO/` för anteckningar). |
| `data/` | Beskrivning av datakällor och kvalitet. Rådata stannar på varje dator. |
| `docs/` | [release.md](docs/release.md) (släpp och uppdateringar), [universe.md](docs/universe.md), [status-punkt-1.md](docs/status-punkt-1.md) (läget för den gemensamma grunden), [marknadsdata.md](docs/marknadsdata.md) och [status-punkt-2.md](docs/status-punkt-2.md) (insamling av marknadsdata), [status-punkt-3.md](docs/status-punkt-3.md) (prisdiagram), [status-rek-3.md](docs/status-rek-3.md) (verklig marknadsdata i appen). |
| `.claude/skills/` | Våra arbetsregler som skills, se [.claude/skills/README.md](.claude/skills/README.md). |

## Kommandon

Kräver Node 22 och Rust (stable). Varje app har sina egna paket.

```bash
npm --prefix app ci && npm --prefix app run tauri dev                                            # Trader_go
npm --prefix apps/trader-go-universe ci && npm --prefix apps/trader-go-universe run tauri dev    # Universe
bash scripts/install-macos.sh                                                                    # bygg båda och installera på den här Macen
```

`install-macos.sh` lägger **TraderGO** och **TraderGO Universe** i `/Applications` (eller
`~/Applications`) som två separata appar med egna program-id. Sedan startas de utan terminal.
Windows-användare installerar från den publika nedladdningssidan (se nedan).

## Så hittar Universe projektet

Universe letar upp din kopia av repot på varje dator. Ingen sökväg med någons användarnamn sparas
i Git. Ordning:

1. En mapp du har valt i appen (**Byt mapp…**), sparad i appens egen datamapp.
2. Miljövariabeln `TRADERGO_ROOT`.
3. I utvecklingsläge: den här mappen.
4. Vanliga platser under hemmappen, t.ex. `~/Documents/GitHub/Trader_go`, `~/GitHub/Trader_go`,
   `~/Developer/Trader_go` och `~/source/repos/Trader_go`.

En mapp räknas som projektet om den har `CLAUDE.md` och `apps/trader-go-universe/`. Universe läser
bara: kartan, kortplaceringarna och inställningarna ligger i appens datamapp, och inget i
projektmappen skapas, ändras, byter namn eller tas bort.

## Samarbete: så hämtar ni varandras ändringar

`SEASTICK/Trader_go` (privat) är den gemensamma källan, och båda arbetar direkt på `main`:
synkronisera → ändra → testa → commit → synkronisera → push. Kommandon, vilka kontroller som ska
köras före push (direkt på `main` körs ingen CI), och tabellen för pågående arbete finns i
[docs/samarbete.md](docs/samarbete.md).

- **Hämta:** `git switch main && git pull --ff-only`. Universe ser ändringarna direkt (filbevakning),
  och Obsidian läser samma filer i `research/`.
- **Pusha:** först `git pull --rebase`, sedan `git push`. Aldrig `--force`.
- **En appuppdatering rör aldrig repot,** och en push uppdaterar inte apparna (se nästa avsnitt).

## Så når en godkänd release de installerade apparna

En push till `main` publicerar **ingenting**. Släpp görs för hand (eller med en `v*`-tagg) i
`desktop-release.yml`, se [docs/release.md](docs/release.md):

1. **Run workflow** med `channel = test` först. Testbyggena heter "Trader_go Updater Test" och
   "TraderGO Universe Test", har egna program-id och följer bara testkanalen.
2. **Run workflow** med `channel = stable`. Körningen pausar tills en av godkännarna svarar
   `approve` i ärendet den skapar.
3. Installationsfilerna, signaturerna och `latest.json` publiceras på den publika sidan
   `SEASTICK/trader-go-releases` (bara byggda appar, aldrig källkod, anteckningar eller nycklar):
   Trader_go i roten, Universe under `universe/`, test under `test/`.
4. De installerade apparna söker uppdatering själva, verifierar signaturen mot den publika
   nyckeln i appen och frågar innan de startar om. Inställningar och data i appens datamapp
   behålls.

Nedladdning första gången: `https://seastick.github.io/trader-go-releases/downloads.html`.
