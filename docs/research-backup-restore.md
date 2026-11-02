# Backup och återställning av Research Engine

## Befintliga backuper

Edwin bekräftade 2026-11-02 att DigitalOcean har sju dagars backup och att
Supabase visar dagliga databasbackuper. Detta är användarverifierat; policy,
senaste körning och leverantörsåterställning har inte kontrollerats via API.
Ingen ny betaltjänst har skapats eller befintlig backuppolicy ändrats.

DigitalOcean säkerhetskopierar dropletens disk, inklusive worker, råarkiv,
manifest, systemd-filer och serverns privata konfiguration. Supabase ligger
separat och behöver sin egen databasbackup. Kontrollera retention och senaste
godkända körning i båda tjänsterna före större driftsändringar. DigitalOcean
backar inte automatiskt upp separata volumes; inga sådana verifierades här.

Källor: https://docs.digitalocean.com/products/backups/details/features/ och
https://supabase.com/docs/guides/platform/backups.

## Genomfört isolerat återställningsprov

`data/audits/fas1-20261102/restore-verification.json` innehåller testresultatet.
En privat export gjordes med servernyckeln utan att ändra produktionen.
Två identiska fullständiga REST-läsningar krävdes och inga jobb fick vara
aktiva. Exporten sparades 0600 i en katalog med 0700.

Följande återställdes i en isolerad PGlite/PostgreSQL-databas från projektets
migrationer: 11 916 candles, 5 481 fundingrader, 1 medlemsrad, 5 jobb,
3 resultat och 7 affärer. Strategi-/hypotestabellerna var tomma. Samtliga
fält jämfördes som typade PostgreSQL-värden, inte bara radantal. Anonym
resultatåtkomst och medlems direktskrivning nekades efter återställningen.

**Avgränsning:** REST-exporten är inte en transaktionell pg_dump och ersätter
inte Supabases backup. Auth-konton/lösenord, Storage-objekt, hemligheter och
workerns flyktiga reservationsplats ingår inte. Testdatabasen använde bara
UUID-platshållare för att kontrollera främmande nycklar. Inga riktiga konton
eller lösenord återställdes och ingen full droplet-/Supabase-katastrofåterställning
utfördes. Därför är denna del av slutgodkännandet fortfarande öppen.

## Upprepa provet

På servern, från den release som innehåller exportverktyget:

```sh
PYTHONPATH=engine /opt/tradergo/venv/bin/python -m traderlab.research_engine.backup \
  --env-file /etc/tradergo/research.env --output /var/backups/tradergo/research
```

Kommandot loggar bara filnamn, radantal och kontrollsumma, aldrig innehåll
eller nycklar. Om data ändras eller ett jobb körs avbryts exporten och tidigare
filer behålls. Ingen automatisk gallring eller schemaläggning infördes eftersom
leverantörernas dagliga backuper redan är aktiva enligt användaren.

Kopiera exporten till en privat testkatalog utanför Git och kör:

```sh
PGLITE_MODULE=/path/to/@electric-sql/pglite/dist/index.js \
  node scripts/verify-research-restore.mjs /private/test/research.json.gz
```

Spara bara den avidentifierade kontrollrapporten i Git. Exportens medlemmar,
jobb och användar-id:n ska inte läggas i repot eller skickas i chatten.

## Full återställning vid driftproblem

1. Välj rätt backup och återställ till en separat droplet/projekt först; undvik
   att skriva över fungerande produktion. En ny betald resurs kräver kostnadsbeslut.
2. Kontrollera serverns SSH-hostnyckel och privata credentials. Starta inte
   workern innan rätt Supabase-projekt, schema och medlemsåtkomst är verifierade.
3. Säkerställ att migrationsversion och kod hör ihop. Kör schema-/RLS-kontroller,
   återläsning av fryst dataset och ett reproducerbart forskningsjobb.
4. Kontrollera att gamla jobbreservationer inte kan skriva resultat; återta bara
   utgångna leases via den befintliga kön. Dubblettskydd ska fortfarande gälla.
5. Dokumentera faktisk återställningstid och dataförlust. Byt aktiv server först
   efter verifiering och behåll den gamla miljön som återgångsväg.

Vid endast en trasig kodrelease kan `/opt/tradergo/current` återställas till
föregående release och workern startas om efter att kön tömts. Det är en
kodåtergång och ersätter inte databasåterställning.
