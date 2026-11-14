# Designuppgradering av Trader_go-appen

Före- och efterbilder från den körande webbbygget (`vite preview`), 1440×900 och 390×844 (mobil), ljust och mörkt. Sidor: Hem, Resultat, Papper, Marknad.

Filnamn: `before-` / `after-` + `{sida}-{desktop|mobil}-{light|dark}.png`.

Inte testat i Tauri-skrivbordsappen på Windows. Ingen release, ingen ändring av `identifier` eller migrationer.

## Verifiering i det riktiga Tauri-skalet (Linux, inte Windows)
`tauri-linux-*.png` är tagna ur den riktiga Tauri-binären (`tauri build --debug --no-bundle`, WebKitGTK) körd i Xvfb 1440×900 utan fönsterhanterare. Det är **inte** Windows/WebView2. Se PR #135 för vad som är och inte är verifierat.
