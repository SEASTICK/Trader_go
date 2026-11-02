# Fas 1: integration av PR #59 och #61

Den kanoniska kön är `traderlab.research_engine.worker`, systemd-enheten
`tradergo-research-worker.service`, miljöfil `/etc/tradergo/research.env` och
Supabase RPC:erna från migration 0003/0004. Global slot, lease, heartbeat,
fencing, avbrott och processgränser gäller för båda jobbsorterna.

Den äldre `server.jobs` är avstängd: direkt PATCH av status skyddade inte mot
flera samtidiga forskningsjobb, saknade fencing och skrev inget payload som
Research Lab kunde läsa. `server.main` är nu en kompatibilitetsingång till den
kanoniska workern och kräver samma CLI-argument. Den gamla installeraren och
enheten kan inte starta en andra worker. De äldre automatiska deploy- och
migreringsflödena har stängts av; att återköra redan tillämpade migrationer eller
ersätta en aktiv venv via rsync är inte en accepterad deployväg.

Marknadssynk är en separat oneshot-tjänst med egen filreservation. Den tar inga
forskningsjobb. En timer kör efter boot och fem minuter efter föregående körning.
Insamlingen börjar 2026-11-02 UTC och går framåt; den varken fyller i 2025 års
slutprov eller ändrar den frysta historiken 2020–2024. Mellanperioden är inte
insamlad av denna tjänst. Alla sex spot/UM-tidsramar ingår. Stängda rader jämförs
och ändras aldrig; pågående rader får uppdateras. Dataluckor och fel stoppar sidan.
Manifest skiljer detta operativa dataflöde från det frysta forskningsdatasetet.

Fas 1-rutornas adapter öppnar inga rådataarkiv. Den kräver originalfilens SHA256
från den verifierade Lab-exporten och använder dess frysta terminsbaslinje med
funding och kostnader. Saknade jämförelsekurvor ersätts aldrig med strategins
kurva. Fas 1-markörer visas på historiska UM-candles, inte dagens spotpris.
Alla fyra registrerade kriterier, inklusive parameterstabilitet, krävs.

Registrerade köjobb är tekniska reproduktioner av redan frysta fönster och
parametrar. De öppnar exakt 120 SHA256-kontrollerade utvecklingsarkiv, utan
nätverksfallback, optimering eller slutprov. Nyckeltal och kurvor måste matcha
originalet exakt. Körningen sparas separat och kan misslyckas eller avbrytas;
registret och REJECT-besluten ändras inte. Nya forskningshypoteser kräver fortsatt
förregistrering i Git och en separat forskningskörning.

Windows-test och driftlarm är undantagna från denna leverans på användarens
uttryckliga begäran. Inga larmmottagare eller nya betaltjänster konfigureras.
