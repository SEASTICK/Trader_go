# Trader_go-appen

Statisk webbsida (Vite + React + TypeScript). Ingen server, inga nycklar. Datan ligger i
`app/data/` och läses direkt av appen.

```bash
cd app
npm ci
npm run dev      # lokalt
npm run build    # bygger till app/dist
```

## Cloudflare Pages (görs av människa, inget hemligt i Git)

- Root directory: `app`
- Build command: `npm run build`
- Build output directory: `dist`
- Skydda sidan med Cloudflare Access (e-post) så bara ni två kommer in.

Appen visar bara. Den handlar inte och ansluter inte till någon börs.

## Datorprogram (Tauri, Windows)

Samma gränssnitt paketeras som ett Windows-program.

```bash
cd app
npm ci
npm run tauri dev     # kör programmet lokalt (kräver Rust)
npm run tauri build   # bygger installationsfilen
```

GitHub Actions (`.github/workflows/windows-build.yml`) bygger en installationsfil (`.exe`) vid
varje pull request (ladda ner under körningens **Artifacts**) och vid varje push till `main`.
Vid push till `main` publiceras den också under **Releases** som `latest` (senaste bygget
ersätter det förra).

Installationsfilen är **inte kodsignerad**, så Windows kan visa "okänd utgivare" första
gången. Välj "Mer info" och "Kör ändå".

Automatiska uppdateringar är inte påslagna än. De kräver en signeringsnyckel som skapas lokalt
och läggs som hemlighet i GitHub, aldrig i Git.
