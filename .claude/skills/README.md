# Skills i Trader_go

Skills läses in när Claude Code körs i det här repot. Skriv `/namn`, eller beskriv vad du vill
göra så används rätt skill.

## Våra egna

| Skill | Används när |
|---|---|
| `ny-hypotes` | En ny idé ska testas. Registrerar den och räknar försöket. |
| `granska-backtest` | Ett resultat ska granskas innan beslut. |
| `pengar-grind` | Riktiga pengar, nycklar eller hävstång kommer på tal. |
| `forskningslogg` | Något ska in i Obsidian-anteckningarna. |
| `hamta-data` | Historik ska hämtas från öppna källor eller kontrolleras. |
| `papper-framat` | En strategi med `READY_FOR_PAPER` ska köras framåt på papper. |
| `riskgranser` | Position, hävstång, short eller nödstopp ska dimensioneras. |
| `release` | En ny version av appen ska släppas, eller en release-körning har misslyckats. |
| `app-design` | Något i appen ska byggas eller ändras visuellt. |
| `ny-ruta` | En ruta ska läggas till i Research, få riktiga siffror eller sållas. |

## Från andra, kopierade och fastlåsta

Läst igenom före kopiering. Filerna uppdateras inte av sig själva, så ny version kräver en ny
genomgång. Alla är MIT-licensierade, och licensen ligger i varje mapp som `LICENSE.upstream`.

| Skill | Källa | Commit |
|---|---|---|
| `backtest-expert` | [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills) | `94c5835` |
| `obsidian-markdown`, `obsidian-bases`, `obsidian-cli`, `json-canvas` | [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | `3ccff53` |

Enda ändringar: sökvägen i `backtest-expert` pekar på `.claude/skills/`, och dess tester är
borttagna.

## Att veta

- **OmniRoute-skillsen** (`omni-auth`, `cli-serve`, `omni-combos-routing`) är borttagna eftersom de inte
  användes och tog plats i varje session. Vill ni ha dem igen: kopiera dem från
  [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute) (commit `b2a6410`) efter en ny genomgång.
- **`obsidian-cli`** kräver att Obsidian är öppet och att dess kommandorad är påslagen.
- **`backtest-expert`** är skriven med aktier som exempel, så anpassa den till krypto. Den
  täcker inte finansieringsränta eller likvidation. Det gör `granska-backtest`.
