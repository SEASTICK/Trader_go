# Forskningsspår

Vi kör flera sorters strategier samtidigt, men bedömer dem i separata spår. Varje spår har sina
beslutskriterier bestämda **innan** någon hypotes i spåret har körts (2026-11-01). Kriterierna ändras inte
i efterhand. Ett nytt kriterium blir ett nytt spår.

Gemensamt för alla spår:

- Antalet försök N räknas över **alla** spår tillsammans, eftersom varje försök ökar risken för slumpfynd.
  t-kravet följer N (Bonferroni, golv 2,0) och anges vid registreringen.
- Avkastning med 2,5 gånger kostnaderna ska vara > 0.
- Godkänt betyder `MORE_RESEARCH`: idén får granskas och sedan testas på den orörda perioden
  (2025-01 till 2026-09) och på papper. Inget i ett spår betyder att strategin tjänar pengar framåt.

| Spår | Namn | Frågan | Kriterier utöver de gemensamma |
|---|---|---|---|
| A | Slå marknaden | Ger strategin bättre riskjusterad avkastning än köp-och-behåll? | t ≥ kravet OCH Sharpe > köp-och-behåll på samma data |
| B | Lägre risk | Ger strategin en jämnare resa med betydligt mindre fall? | t ≥ kravet OCH max nedgång minst 40 % mindre än köp-och-behåll (till exempel −45 % mot −76 %) |
| C | Marknadsneutral | Tjänar strategin pengar oberoende av om BTC går upp eller ned? | t ≥ kravet OCH \|beta mot BTC\| ≤ 0,2 (dagsavkastning mot BTCUSDT spot 1d) |

Hypoteserna H-0001 till H-0005 hör till spår A, eftersom de registrerades med A:s kriterier. De flyttas inte
till ett annat spår i efterhand, även om ett resultat skulle ha klarat ett annat spårs krav.

## Säkrade rutor (spår C)

En säkrad ruta är spot lång och termin kort med samma belopp. Priset tar då nästan ut sig, och det som blir kvar
är finansieringsräntan och basen (skillnaden mellan termin och spot). Motorn räknar:

- två ben per affär, så kostnaderna dubblas,
- säkringen balanseras om vid varje stapel utan extra kostnad (en förenkling som gör resultatet något för bra),
- avkastningen per säkrat belopp. I verkligheten behövs kapital till båda benen, så avkastningen på hela
  kapitalet blir ungefär hälften med 1 gångers marginal på terminen.

Se `engine/traderlab/hedge.py` och `engine/traderlab/batch.py`.
