---
name: riskgranser
description: Använd när position, hävstång, short eller terminer ska dimensioneras, eller när gränser och nödstopp ska definieras och räknas ut. Gäller papper lika mycket som live.
---

# Riskgränser

Gränserna ligger utanför strategin och kan inte stängas av av den. De gäller på papper från
början, så att beteendet är detsamma den dag någon ändå beslutar något annat. Riktiga pengar
kräver `pengar-grind`.

## Gränser som alltid ska finnas (siffror väljer ni, skriv ned dem)

- Max per position, max total exponering och max förlust per dag.
- Max antal affärer per dag, som skydd mot en bugg som handlar i loop.
- **Nödstopp:** en tydlig åtgärd som stoppar alla nya order, och en regel för när den slås på
  (till exempel förlust över gräns, uteblivna data, avvikelse från förväntat beteende).
- Vad boten gör när data saknas eller är gammal: ingen ny affär.

## Dimensionering

- Utgå från förlusten ni accepterar per affär, inte från hur mycket konto som finns.
  Storlek = tillåten förlust / avstånd till stopp.
- Ta med avgifter och slippage vid stoppet. Ett stopp fylls sällan på exakt nivå.
- Kryptos svansrisk är verklig: räkna med rörelser större än det historiska urvalet visar.

## Short och terminer

För varje terminsposition, räkna och skriv ned:

1. **Likvidationsnivå** från hävstång, underhållsmarginal och avgifter. Ange avståndet i procent
   och i multipler av typisk daglig rörelse.
2. **Finansieringsränta:** vad den kostar per dag vid den storlek och hållningstid strategin har.
   Håll ett stresscenario med dubbla räntan.
3. **Gap och spikar:** likvidation kan ske på ett enskilt högsta/lägsta pris. Lågt avstånd till
   likvidation i förhållande till stoppet är ett fel i designen.
4. **Short-squeeze:** förlusten är i princip obegränsad. Stoppet måste finnas utanför strategin.
- Börsnycklar (om de någonsin skapas av er) ska sakna uttagsrätt och helst vara IP-låsta.
  Claude skapar eller hanterar dem aldrig.

## Resultat

Svara med en kort tabell: gräns, värde, hur den kontrolleras, vem som kan ändra den. Saknas ett
värde är strategin inte klar för nästa steg i livscykeln. Ändring av en gräns efter att ett
framåttest startat är en ny strategi (se `papper-framat`).
