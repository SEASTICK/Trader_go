import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf-8")) as { version: string };

function git(cmd: string, fallback: string): string {
  try {
    return execSync(cmd, { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
  } catch {
    return fallback;
  }
}

// Uppdateringsflödet är Trader_go:s eget (app/src/features/updates), inte en kopia. dedupe gör att
// filerna därifrån använder Universes React och Tauri-paket, så app/ behöver inte vara installerad.
const updates = fileURLToPath(new URL("../../app/src/features/updates", import.meta.url));
const repo = fileURLToPath(new URL("../..", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@trader-go/updates": updates },
    dedupe: ["react", "react-dom", "@tauri-apps/api", "@tauri-apps/plugin-updater", "@tauri-apps/plugin-process"],
  },
  // Egen port så att båda apparna kan köras samtidigt i utvecklingsläge.
  server: { port: 5174, strictPort: true, fs: { allow: [repo] } },
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
    // Byggcommit, så att två installationer går att jämföra. "+ändrad" = byggt med ocommittade ändringar.
    __COMMIT__: JSON.stringify(process.env.CF_PAGES_COMMIT_SHA?.slice(0, 7) ?? (git("git rev-parse --short HEAD", "okänd") + (git("git status --porcelain --untracked-files=no", "") ? "+ändrad" : ""))),
    __COMMIT_MSG__: JSON.stringify(git("git log -1 --format=%s", "")),
    __BUILT_AT__: JSON.stringify(new Date().toISOString()),
  },
});
