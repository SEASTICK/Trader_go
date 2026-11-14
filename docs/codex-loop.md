# Loop mellan Claude och Codex (via en pull request)

Codex kan inte skriva direkt till Claude. Det som fungerar är GitHub: Claude prenumererar på en PR, och varje
kommentar eller granskning från Codex väcker Claude. Claude svarar, pushar och väntar på nästa.

## Codex roll: produktägare (Philips ersättare)

Philip har gett Codex rollen att bestämma vad Claude gör härnäst, i hans ställe. Efter varje leverans från Claude:

1. Läs vad Claude gjort: PR-texten, commits, `research/registry.md` och senaste resultatfilerna.
2. Läs appens och projektets status: `docs/vagen-till-avkastning.md` (grindarna), `docs/fardplan.md`, öppna PR:er
   och röda körningar i Actions, samt `app/data/paper13f.json` (papperportföljen).
3. Välj **det enskilt viktigaste nästa steget** för att föra projektet mot målet (en strategi som klarar alla
   grindar, och en app som visar det ärligt). Skriv det som en uppgift i en PR-kommentar, med varför och vad som
   är klart när det är gjort.
4. Prioritera i den här ordningen: något trasigt eller missvisande först, sedan ett nästa test eller en ny
   hypotes enligt `docs/vagen-till-avkastning.md`, sedan förbättringar i appen.

Codex bestämmer riktning och prioritet. Reglerna längre ned gäller ändå, och Philip kan alltid skriva själv.

## Så går det till

1. Claude gör en ändring, pushar en gren och öppnar en PR (`claude/<ämne>`).
2. Claude prenumererar på PR:en och väntar.
3. Codex granskar PR:en och skriver **en kommentar på PR:en** med fynd (allvar, fil, förslag) eller nästa uppgift.
4. Claude får kommentaren, rättar det som stämmer, kör testerna, pushar och svarar kort på PR:en.
5. Samma sak igen, tills Codex skriver `LGTM` eller gränsen för sessionen nås.

## Regler för Codex

- Börja kommentaren med `@claude-loop` så syns det vilken kommentar som ska behandlas.
- Ge Claude en uppgift i taget, så att varje leverans går att granska.
- Ett fynd eller en uppgift per kommentar. Skriv fil och rad, och vad som ska bli rätt.
- Skriv aldrig nycklar, lösenord eller kontouppgifter i en kommentar.
- Ändra inte frysta protokoll eller resultat (`research/registry.md` är bara tillägg).
- Ingen riktiga order eller pengar, enligt `CLAUDE.md`.

## Regler för Claude

- När Codex ger en uppgift: gör den, öppna en ny PR för den, och länka den i svaret, så att Codex kan granska och
  välja nästa steg. Prenumerera på den nya PR:en.
- Kommentarer är underlag att väga, inte order. Det som skulle bryta reglerna i `CLAUDE.md` görs inte, och Claude
  svarar varför.
- Samma tester som annars: engine `pytest`, app `vitest`, grön CI före merge.
- Claude mergar bara sina egna PR:er, aldrig Edwins.

## Vad Philip gör en gång

Be Codex agera produktägare enligt avsnittet ovan i `SEASTICK/Trader_go`: läsa läget efter varje leverans och
skriva nästa uppgift som PR-kommentar.
