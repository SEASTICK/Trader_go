#!/usr/bin/env bash
# Bygger och installerar TraderGO och TraderGO Universe på den här Macen, för dess arkitektur.
#   bash scripts/install-macos.sh              bygg och installera båda
#   bash scripts/install-macos.sh --no-build   installera de senast byggda paketen
# Installerar i /Applications, eller i ~/Applications om /Applications inte är skrivbar.
# Rör inga andra appar och nollställer inte Launchpad: apparna registreras med lsregister, som
# Finder själv använder.
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(uname)" = "Darwin" ] || { echo "Bara för macOS." >&2; exit 1; }

# Lokala byggen har ingen uppdateringsnyckel, så uppdateringsfilerna stängs av. Installerade appar
# uppdateras ändå från den publika uppdateringssidan när en godkänd release finns.
build() {
  local dir="$1"
  [ -d "$dir/node_modules" ] || npm --prefix "$dir" ci
  npm --prefix "$dir" run tauri -- build --bundles app --config '{"bundle":{"createUpdaterArtifacts":false}}'
}
if [ "${1:-}" != "--no-build" ]; then
  build app
  build apps/trader-go-universe
fi

dest=/Applications
[ -w "$dest" ] || { dest="$HOME/Applications"; mkdir -p "$dest"; }
lsregister=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister

install_app() {
  local name="$1" built="$2"
  [ -d "$built" ] || { echo "Hittar inte $built. Kör utan --no-build." >&2; exit 1; }
  if pgrep -f "$dest/$name.app/Contents/MacOS/" >/dev/null; then
    echo "Avslutar $name innan den ersätts…"
    osascript -e "tell application \"$dest/$name.app\" to quit" >/dev/null 2>&1 || true
    sleep 2
  fi
  # Ersätter bara just den här appen. Inställningar och data ligger i ~/Library och rörs inte.
  rm -rf "$dest/$name.app.new"
  ditto "$built" "$dest/$name.app.new"
  rm -rf "$dest/$name.app"
  mv "$dest/$name.app.new" "$dest/$name.app"
  "$lsregister" -f "$dest/$name.app"
  # Byggkopian ska inte synas som en egen app i Launchpad eller Spotlight: byggmappen indexeras
  # inte, och kopians registrering tas bort (bara den, inga andra appar).
  touch "${built%/release/*}/.metadata_never_index"
  "$lsregister" -u "$built" 2>/dev/null || true
  echo "Installerad: $dest/$name.app"
}

# Trader_go heter TraderGO på Mac (app/src-tauri/tauri.macos.conf.json); samma program-id som på Windows.
install_app "TraderGO" "app/src-tauri/target/release/bundle/macos/TraderGO.app"
install_app "TraderGO Universe" "apps/trader-go-universe/src-tauri/target/release/bundle/macos/TraderGO Universe.app"
echo "Klart. Apparna finns i Launchpad och i $dest."
