import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";

const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf-8")) as { version: string };
// Uppdateringsadressen som byggs in i appen. Release-flödet skriver om den för testkanalen före bygget,
// så Status visar alltid den kanal och adress som uppdateraren faktiskt använder.
const tauriConf = JSON.parse(readFileSync(new URL("./src-tauri/tauri.conf.json", import.meta.url), "utf-8")) as { plugins: { updater: { endpoints: string[] } } };
const updateFeed = tauriConf.plugins.updater.endpoints[0] ?? "";

function git(cmd: string, fallback: string): string {
  try {
    return execSync(cmd, { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
  } catch {
    return fallback;
  }
}

export default defineConfig({
  plugins: [react()],
  // Appen läser research/registry.md (utanför app/) när den byggs.
  server: { fs: { allow: [".."] } },
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
    __COMMIT__: JSON.stringify(process.env.CF_PAGES_COMMIT_SHA?.slice(0, 7) ?? git("git rev-parse --short HEAD", "okänd")),
    __COMMIT_MSG__: JSON.stringify(git("git log -1 --format=%s", "")),
    __BUILT_AT__: JSON.stringify(new Date().toISOString()),
    __UPDATE_FEED__: JSON.stringify(updateFeed),
    __UPDATE_CHANNEL__: JSON.stringify(/\/test\//.test(updateFeed) ? "test" : "stable"),
  },
});
