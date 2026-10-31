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
