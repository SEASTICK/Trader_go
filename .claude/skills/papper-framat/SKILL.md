---
name: papper-framat
description: Använd när en strategi har beslutet READY_FOR_PAPER och ska köras framåt på papper, eller när ett papperstest ska följas upp och jämföras med backtestet. Inga riktiga order.
---

# Pappershandel framåt

Backtest visar vad som hade hänt. Papper framåt visar om det stämmer på data strategin aldrig
sett. Allt här sker utan riktiga pengar och utan börskonto. Kommer riktiga pengar på tal, stanna
och använd `pengar-grind`.

## Innan start

1. `READY_FOR_PAPER` finns i `research/registry.md` för strategin.
2. **Frys strategin:** committa exakt kod, parametrar och data-/kostnadsantaganden, och notera
   commit-hashen i registret. Från nu gäller regel 3 i `CLAUDE.md`: en ändring är en ny
   strategi, ett nytt id och en ny klocka.
3. **Räkna ut i förväg** hur många affärer som behövs, från strategins egen spridning i
   backtestet, och skriv det i registret. Skriv också vad som räknas som misslyckande: till
   exempel avvikelse från backtestets takt eller en förlust större än kriteriet.
4. Bestäm slutdatum eller antal affärer innan start. Avbryt inte för att det ser bra eller
   dåligt ut.

## Under körning

- Beslut på stängd stapel, fyllning vid nästa stapels öppning, med samma avgifter, spread och
  slippage som i backtestet. Använd gärna pessimistiska fyllningar.
- Logga varje signal, simulerad affär och utebliven affär i en append-only-fil under
  `paper/<id>/`. Rader tas aldrig bort eller ändras.
- Använd bara publik data. Inga nycklar.
- Avbrott, datafel och missade staplar loggas som händelser och räknas med.

## Uppföljning

Jämför mot backtestet, med siffror:

- affärstakt, innehavstid och exponering
- avkastning efter kostnader, med osäkerhetsintervall
- verklig kontra antagen slippage
- avvikelse från förväntad fördelning (en enskild bra vecka bevisar ingenting)

## Beslut

När det förutbestämda antalet affärer eller slutdatum nåtts skrivs resultatet på en ny rad i
registret. Att det håller på papper är inget löfte om live. Nästa steg är en diskussion enligt
`pengar-grind`, inte ett automatiskt byte. Misslyckas testet är `REJECT` ett fullgott utfall.
