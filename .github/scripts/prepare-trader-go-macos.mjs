#!/usr/bin/env node
// Sätter releaseversionen och kanalens identitet för Mac-bygget av Trader_go i CI. Gör samma sak som
// Windows-jobbets steg "Set release version and channel identity", plus Mac-namnet i
// tauri.macos.conf.json, så att ett testbygge aldrig heter TraderGO.app och krockar med den riktiga appen.
//   node .github/scripts/prepare-trader-go-macos.mjs <stable|test> <X.Y.Z>
import { readFileSync, writeFileSync } from "node:fs";

const [channel, version] = process.argv.slice(2);
if (!["stable", "test"].includes(channel) || !/^\d+\.\d+\.\d+$/.test(version ?? "")) {
  console.error("usage: prepare-trader-go-macos.mjs <stable|test> <X.Y.Z>");
  process.exit(2);
}
const PAGES = process.env.RELEASES_PAGES_URL ?? "https://seastick.github.io/trader-go-releases";
const json = (p) => JSON.parse(readFileSync(p, "utf8"));
const save = (p, v) => writeFileSync(p, JSON.stringify(v, null, 2) + "\n");

const pkg = json("app/package.json");
pkg.version = version;
save("app/package.json", pkg);

const confPath = "app/src-tauri/tauri.conf.json";
const conf = json(confPath);
conf.version = version;
if (channel === "test") {
  conf.identifier = "com.seastick.tradergo.updatertest";
  conf.productName = "Trader_go Updater Test";
  conf.plugins.updater.endpoints = [`${PAGES}/test/latest.json`];
  const macPath = "app/src-tauri/tauri.macos.conf.json";
  const mac = json(macPath);
  mac.productName = "TraderGO Updater Test";
  for (const w of mac.app?.windows ?? []) w.title = "TraderGO Updater Test";
  save(macPath, mac);
}
save(confPath, conf);

const cargoPath = "app/src-tauri/Cargo.toml";
writeFileSync(cargoPath, readFileSync(cargoPath, "utf8").replace(/(\[package\][\s\S]*?^version\s*=\s*")[^"]+(")/m, `$1${version}$2`));

const check = [json("app/package.json").version, json(confPath).version, /^version\s*=\s*"([^"]+)"/m.exec(readFileSync(cargoPath, "utf8"))[1]];
if (check.some((v) => v !== version)) {
  console.error(`Could not set the release version consistently: ${check.join(", ")}`);
  process.exit(1);
}
console.log(`Prepared Trader_go ${version} for macOS on the ${channel} channel`);
