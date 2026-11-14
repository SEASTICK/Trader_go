# Designuppgradering av Trader_go-appen

Före- och efterbilder från den körande webbbygget (`vite preview`), 1440×900 och 390×844 (mobil), ljust och mörkt. Sidor: Hem, Resultat, Papper, Marknad, samt Research Lab (flikarna Resultat, Fas 2, Utforskning) och Status (`*-researchlab-*`, `*-status-*`).

Filnamn: `before-` / `after-` + `{sida}-{desktop|mobil}-{light|dark}.png`.

Inte testat i Tauri-skrivbordsappen på Windows. Ingen release, ingen ändring av `identifier` eller migrationer.

## Verifiering i det riktiga Tauri-skalet (Linux, inte Windows)
`tauri-linux-*.png` är tagna ur den riktiga Tauri-binären (`tauri build --debug --no-bundle`, WebKitGTK) körd i Xvfb 1440×900 utan fönsterhanterare. Det är **inte** Windows/WebView2. Se PR #135 för vad som är och inte är verifierat.

## Research Lab och Status (andra omgången)
Före/efter finns för dator (1440×900) och mobil (390×844), ljust och mörkt. `after-fokus-researchlab-desktop-light.png` visar synlig tangentbordsfokus.
Kontroller (webbygget, Playwright): ingen horisontell overflow vid 390, 700 och 1440 px, ljust och mörkt, i alla fyra vyer; Tab genom varje vy ger synlig fokusmarkering på alla fokuserbara element; inga JS-fel.
Windows-röktestet (`app/smoke/desktop-smoke.cjs`) täcker även Research Lab och Status: rubrik och ingen horisontell overflow i normal storlek och vid 700 px.
