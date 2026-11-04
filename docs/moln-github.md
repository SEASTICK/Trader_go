# GitHub, DigitalOcean och Supabase: hur de hänger ihop

## Läget (2026-11-04)

| Del | Vad som finns | Vem satte upp |
|---|---|---|
| Supabase | Projekt med tabeller, medlemsspärr (RLS), jobbkö och H-0013-kö (migrationer 0001–0005, körda en gång var i SQL Editor). Dagliga backuper (Pro). | Edwin |
| DigitalOcean | Dropleten kör `tradergo-research-worker` (forskningskön) och `tradergo-market-sync` (marknadsdata var 5:e minut). Supabase-nyckeln ligger bara i `/etc/tradergo/research.env` på servern. 7 dagars backup. | Edwin |
| Appen | Research Lab loggar in mot Supabase med den publika nyckeln (finns i koden, är inte hemlig). | Edwin |
| GitHub | Bygger och släpper apparna. **Nytt:** driftsätter workern och kontrollerar servern (nedan). | Philip (Claude) |

## Vad GitHub gör nu

- **Research deploy** (Actions → Research deploy → Run workflow): bygger workerpaketet från en commit på `main`,
  skapar ett ärende och väntar på `approve` från SEASTICK eller edwinfighter42-star. Sedan görs stegen i
  [fas2-driftsattning.md](fas2-driftsattning.md) automatiskt: paketet verifieras, workern stoppas bara när inget
  jobb pågår, installeras med `install.sh`, startas och kontrolleras med `check-single-worker.sh`. Föregående
  release ligger kvar för återgång. Ärendet väntar högst 2 timmar (väntan drar Actions-minuter), sedan avbryts
  körningen utan att något ändrats.
- **Research health** (var 6:e timme, och för hand): kontrollerar att workern kör, att det finns exakt en, att
  marknadssynken har lyckats de senaste 30 minuterna och att disken inte är full. Misslyckas den skickar GitHub
  ett mejl. Den bara läser.

**Medvetet inte automatiskt:** Supabase-migrationer. De körs fortfarande en gång var i SQL Editor, efter
granskning, enligt Edwins ordning (koden först, migrationen sist). GitHub får därför ingen databasnyckel alls.

## Det du gör en gång (cirka 10 minuter)

Klistra aldrig in nycklar i chatten. De ska bara in i GitHub och på servern.

**1. Skapa en egen nyckel för GitHub** på din dator:

```bash
ssh-keygen -t ed25519 -C "github-actions-tradergo" -f ~/.ssh/tradergo_github -N ""
```

**2. Lägg till den publika delen på servern.** Logga in som vanligt (`ssh root@SERVERNS_IP`) och kör, med
innehållet i `~/.ssh/tradergo_github.pub` inklistrat:

```bash
echo "INNEHÅLLET_I_tradergo_github.pub" >> /root/.ssh/authorized_keys
```

**3. Hämta serverns värdnyckel** (så att GitHub vägrar ansluta till en falsk server). Kör på din dator:

```bash
ssh-keyscan -t ed25519 SERVERNS_IP
```

Jämför fingeravtrycket med det Edwin verifierade (`ssh-keygen -lf` på raden, eller DigitalOcean Web Console:
`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`). Samma värde = rätt server.

**4. Lägg in tre hemligheter** i GitHub: Trader_go → Settings → Secrets and variables → Actions →
New repository secret.

| Namn | Värde |
|---|---|
| `SERVER_HOST` | Dropletens IP-adress |
| `SERVER_SSH_KEY` | Hela innehållet i den hemliga filen `~/.ssh/tradergo_github` |
| `SERVER_KNOWN_HOSTS` | Raden från steg 3 (börjar med IP-adressen, sedan `ssh-ed25519 ...`) |

**5. Prova:** Actions → Research health → Run workflow. Grönt = GitHub når servern och allt kör.

Vill ni ta bort GitHubs åtkomst: ta bort raden `github-actions-tradergo` ur `/root/.ssh/authorized_keys`.
