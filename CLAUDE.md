# Trader_go

En tradingbot som byggs av två personer för eget bruk. Målet är att hitta, verifiera
och kombinera små kanter utan att lura oss själva.

Projektets långsiktiga mål och fasindelning finns i [målbild och färdplan](docs/fardplan.md).
Målbilden är inte ett livebeslut; samtliga nuvarande säkerhets- och paper-regler gäller fortsatt.

## Regler som alltid gäller

1. **Inga riktiga pengar utan uttryckligt beslut.** Allt körs på historik eller papper.
   Se skillen `pengar-grind`. Lägg aldrig en riktig order på eget initiativ.
2. **Hypotesen skrivs ned före resultatet.** Se `ny-hypotes`. Misslyckade försök tas
   aldrig bort och räknas alltid med.
3. **Ändra aldrig en strategi som testas framåt.** En ändring är en ny strategi och ett
   nytt test, och klockan börjar om.
4. **Inga hemligheter i Git.** API-nycklar ligger i `.env`, som inte committas. Börsnycklar
   får aldrig ha uttagsrätt.
5. **Säg som det är.** `REJECT` är ett bra utfall. Presentera aldrig ett backtest som en
   prognos, och lova aldrig avkastning. Claude är inte licensierad rådgivare och ger inte
   personlig placeringsrådgivning.

## Hur Claude arbetar (Philips beslut 2026-11-05)

Claude arbetar självständigt och frågar inte om lov: merga, pusha, köra flöden och förbättra är tillåtet utan
fråga. Undantagen är kvar eftersom de skyddar mot verklig skada: inga riktiga pengar eller order (regel 1),
inga hemligheter i Git (regel 4), ingen betaltjänst utan att den redan är vald, och Edwins pågående arbete
(`docs/samarbete.md`) skrivs inte över.

## Standardantaganden i ett test

- Beslut på stängd stapel, fyllning vid nästa stapels öppning.
- Avgifter, spread och slippage är alltid med. Finansieringsränta och likvidation är med
  när positionen ligger på terminer.
- Gallring mellan träning och test när etiketten tittar framåt.

## Skrivbordsapparna

`app/` är **Trader_go** och `apps/trader-go-universe/` är **TraderGO Universe** (projektkartan). Se
[README.md](README.md), [app/README.md](app/README.md), [docs/release.md](docs/release.md) och
[docs/universe.md](docs/universe.md). Släpp görs för hand enligt `docs/release.md`.

- Trader_go är bara för papperstrading: lägg aldrig till mäklarkoppling, orderkod eller nyckellagring.
- Universe är bara läsning: den får aldrig skapa, ändra, byta namn på, ta bort eller "reparera" filer i
  projektmappen.
- Ändra aldrig `identifier` i någon av apparnas `tauri.conf.json`, och ändra aldrig en utgiven
  migration i `app/src-tauri/src/db.rs`.
- Obsidian-valvet är `research/`.

## Skills

Se [.claude/skills/README.md](.claude/skills/README.md). Våra egna regler går före
tredjepartsskills. Säger `backtest-expert` "Deploy" betyder det ändå bara att idén får gå
vidare till papper.

## Obsidian

Skillen `obsidian-tradergo` sköter forskning, beslut, strategier, backtestsammanfattningar och
pappersjournal i Obsidian. Använd den bara när någon uttryckligen ber om en Obsidian-uppgift.

- Valvet är `research/`. Skillen får bara röra `research/TraderGO/`; `.obsidian/` och allt annat
  är undantaget.
- Läsning är standard. Nya anteckningar och ändringar är tillåtna. Radera aldrig anteckningar; byt hellre
  namn eller markera dem som inaktuella.
- Inga lösenord, nycklar eller kontouppgifter i anteckningar.
- Stora dataset och resultattabeller ligger i repot, inte i Obsidian. Anteckningen länkar dit.

## Fas 2 – gemensam checklista

Efter varje kodändring eller verifiering som berör H-0013/Fas 2: läs och uppdatera
[checklistan](docs/fas2-checklista.md) via `docs/fas2-status.json` i samma leverans.
Markera bara granskat, verifierat arbete som klart och ange kod-/testunderlag.
Regenerera med `python3 scripts/render-fas2-checklist.py` och kontrollera med `--check`.
Att koden finns, är pushad eller har ett grönt deltest räcker inte för att godkänna hela funktionen.
Ändra inte frysta protokoll eller resultat. Håll lokal kod, driftsättning och publicering åtskilda.
