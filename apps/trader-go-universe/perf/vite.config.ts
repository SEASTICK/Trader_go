// Bygger mätsidan (perf/index.html) med produktionsinställningar. Utdata går till PERF_OUT (utanför repot).
import { defineConfig, mergeConfig } from "vite";
import base from "../vite.config";
import { fileURLToPath } from "node:url";

export default mergeConfig(base, defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  base: "./",
  build: { outDir: process.env.PERF_OUT ?? "dist", emptyOutDir: true, minify: process.env.PERF_MINIFY !== "0" },
}));
