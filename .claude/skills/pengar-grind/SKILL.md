---
name: pengar-grind
description: Använd när någon vill handla med riktiga pengar, koppla en börs eller mäklare, skapa API-nycklar, höja hävstång, eller flytta en strategi från papper till live.
---

# Pengar-grind

Stanna här innan riktiga pengar blir inblandade. Claude lägger aldrig en riktig order, skapar
aldrig konton och skriver aldrig in nycklar eller lösenord. Det gör ni själva. Detta är inte
placeringsrådgivning.

## Livscykel

`Idé → Research → Fryst → Papper → Liten live → Live → Pensionerad`

Inget steg får hoppas över. Visa vilket steg strategin är på och vad som saknas till nästa.

## Krav före liten live

1. Beslutet `READY_FOR_PAPER` finns i `research/registry.md`.
2. Strategin har gått framåt på papper, fryst, med ett antal affärer som räknats ut i förväg
   från strategins egen spridning.
3. Resultatet efter kostnader håller, och beteendet stämmer med backtestet: takt, innehavstid
   och exponering.
4. Ni har båda skrivit ned hur mycket ni har råd att förlora helt, och vad som stoppar boten.
5. Båda har sagt ja i chatten eller i en pull request. Ett ja gäller bara det steget.

## Nödvändigt skydd

- Börsnycklar utan uttagsrätt och helst låsta till serverns IP-adress.
- Hårda gränser utanför strategin: per position, totalt och per dag, samt ett nödstopp.
- Terminer och hävstång kräver en egen genomgång av likvidationsrisken.

## Andras pengar

Var och en handlar på sitt eget konto. Om någon vill samla ihop pengar eller handla åt andra,
särskilt mot betalning, kan det kräva tillstånd från Finansinspektionen. Stanna och ta det
med en jurist innan något byggs.
