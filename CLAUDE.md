# Trader_go

En tradingbot som byggs av två personer för eget bruk. Målet är att hitta, verifiera
och kombinera små kanter utan att lura oss själva.

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

## Standardantaganden i ett test

- Beslut på stängd stapel, fyllning vid nästa stapels öppning.
- Avgifter, spread och slippage är alltid med. Finansieringsränta och likvidation är med
  när positionen ligger på terminer.
- Gallring mellan träning och test när etiketten tittar framåt.

## Skills

Se [.claude/skills/README.md](.claude/skills/README.md). Våra egna regler går före
tredjepartsskills. Säger `backtest-expert` "Deploy" betyder det ändå bara att idén får gå
vidare till papper.

## Skrivbordsappen

`app/` är en Tauri-app för macOS och Windows. Den uppdateras via GitHub Releases när något
pushas till `main` (se [app/README.md](app/README.md)). Appen är bara för papperstrading: lägg
aldrig till mäklarkoppling, orderkod eller nyckellagring. Ändra aldrig `identifier` eller en
utgiven migration i `db.rs`.
