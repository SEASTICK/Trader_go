# Kurskälla för amerikanska aktier (Tiingo)

Investerarspåret (H-0016, H-0017 och papperportföljen på sidan Investerare) behöver dagliga aktiekurser.
Stooq blockerar automatiska hämtningar från molnservrar, och det kringgås inte. Tiingo har ett officiellt API
med en gratis nyckel.

## Det du gör en gång (cirka 3 minuter)

1. Gå till **tiingo.com** → **Sign Up** och skapa ett gratiskonto.
2. Logga in → klicka på ditt namn uppe till höger → **Account** → **API** → **Token**. Kopiera nyckeln.
3. GitHub: **SEASTICK/Trader_go → Settings → Secrets and variables → Actions → New repository secret**.
   - Name: `TIINGO_API_KEY`
   - Secret: nyckeln
   - **Add secret**

Klistra aldrig in nyckeln i en chatt eller i en fil i repot.

## Vad som händer sedan

- **Actions → Research 13F → Run workflow**, hypotes `H-0016`: kör 13F-testet. Gratisnivån tillåter 50 anrop
  i timmen, så första körningen tar några timmar (cirka 390 aktier). Kurserna sparas i en cache, och en körning
  som avbryts fortsätter där den slutade nästa gång.
- Samma sak med hypotes `H-0017` för Pelosi.
- **Paper 13F** körs varje lördag och uppdaterar papperportföljen på sidan Investerare.

Resultaten hamnar på grenen `bot/h-0016-resultat` respektive `bot/h-0017-resultat` och granskas innan de förs in
i registret.
