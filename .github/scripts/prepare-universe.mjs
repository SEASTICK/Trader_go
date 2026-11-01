#!/usr/bin/env node
// Sätter releaseversionen och kanalens identitet för TraderGO Universe före ett bygge i CI.
//   node .github/scripts/prepare-universe.mjs <stable|test> <X.Y.Z>
// Testkanalen får eget program-id, namn och uppdateringsadress, så ett testbygge aldrig ersätter den
// riktiga appen. Det stabila id:t com.seastick.tradergo.universe ändras aldrig.
import { readFileSync, writeFileSync } from "node:fs";

const [channel, version] = process.argv.slice(2);
if (!["stable", "test"].includes(channel) || !/^\d+\.\d+\.\d+$/.test(version ?? "")) {
  console.error("usage: prepare-universe.mjs <stable|test> <X.Y.Z>");
  process.exit(2);
}
const PAGES = process.env.RELEASES_PAGES_URL ?? "https://seastick.github.io/trader-go-releases";
const dir = "apps/trader-go-universe";
const json = (p) => JSON.parse(readFileSync(p, "utf8"));
const save = (p, v) => writeFileSync(p, JSON.stringify(v, null, 2) + "\n");

const pkgPath = `${dir}/package.json`;
const pkg = json(pkgPath);
pkg.version = version;
save(pkgPath, pkg);

const confPath = `${dir}/src-tauri/tauri.conf.json`;
const conf = json(confPath);
conf.version = version;
if (channel === "test") {
  conf.identifier = "com.seastick.tradergo.universe.updatertest";
  conf.productName = "TraderGO Universe Test";
  conf.plugins.updater.endpoints = [`${PAGES}/test/universe/latest.json`];
}
save(confPath, conf);

const cargoPath = `${dir}/src-tauri/Cargo.toml`;
writeFileSync(cargoPath, readFileSync(cargoPath, "utf8").replace(/(\[package\][\s\S]*?^version\s*=\s*")[^"]+(")/m, `$1${version}$2`));

const check = [json(pkgPath).version, json(confPath).version, /^version\s*=\s*"([^"]+)"/m.exec(readFileSync(cargoPath, "utf8"))[1]];
if (check.some((v) => v !== version)) {
  console.error(`Could not set the Universe version consistently: ${check.join(", ")}`);
  process.exit(1);
}
console.log(`Prepared TraderGO Universe ${version} on the ${channel} channel`);
