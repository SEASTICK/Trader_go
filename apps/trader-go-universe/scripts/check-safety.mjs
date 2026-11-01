#!/usr/bin/env node
// Kontroll vid varje `npm test`: Universe är bara läsning och bara papper. Bryter om koden får
// mäklar- eller börskopplingar, orderkod eller nyckellagring, eller om appen får rättigheter eller
// plugins som kan skriva i filsystemet eller köra program. Ren Node, fungerar på Windows och macOS.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const failures = [];

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

const sources = [join(root, "src"), join(root, "src-tauri", "src")]
  .flatMap(walk)
  .filter((p) => /\.(rs|ts|tsx)$/.test(p));
const broker = /ccxt|binance|bybit|kraken|coinbase|alpaca|interactive ?brokers|ibkr|place_?order|create_?order|submit_?order|new_?order|api_?secret|withdraw/i;
for (const file of sources) {
  readFileSync(file, "utf8").split(/\r?\n/).forEach((line, i) => {
    if (broker.test(line)) failures.push(`${relative(root, file)}:${i + 1}: mäklar-, order- eller nyckelkod: ${line.trim()}`);
  });
}

const caps = JSON.parse(readFileSync(join(root, "src-tauri", "capabilities", "default.json"), "utf8"));
const allowed = new Set(["core:default", "updater:default", "process:allow-restart"]);
for (const perm of caps.permissions) {
  const id = typeof perm === "string" ? perm : perm.identifier;
  if (!allowed.has(id)) failures.push(`capabilities/default.json: rättigheten ${id} är inte tillåten i Universe`);
}

const cargo = readFileSync(join(root, "src-tauri", "Cargo.toml"), "utf8");
for (const plugin of ["tauri-plugin-fs", "tauri-plugin-shell", "tauri-plugin-sql", "tauri-plugin-http", "tauri-plugin-stronghold"]) {
  if (cargo.includes(plugin)) failures.push(`Cargo.toml: ${plugin} hör inte hemma i en app som bara läser`);
}

if (failures.length) {
  console.error(failures.join("\n"));
  console.error("Universe är bara läsning och bara papper (se CLAUDE.md och docs/universe.md).");
  process.exit(1);
}
console.log(`Universe safety check OK (${sources.length} källfiler)`);
