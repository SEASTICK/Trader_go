// Röktest av skrivbordsappen. Startar den riktiga Tauri-binären (Windows: WebView2), kopplar Playwright till webbvyn via
// Chrome DevTools-protokollet och kontrollerar att Hem, Resultat, Papper och Marknad renderar och att temat kan växlas,
// utan JS-fel och utan horisontell overflow. Datalagret är tomt: Marknad får inte antyda att prisdata finns.
// Testar INTE diagraminteraktion med riktig data. Bara läsning och klick, inga nycklar, inga order, ingen release.
//
//   node desktop-smoke.cjs <sökväg-till-trader-go.exe>        (kör mot Tauri/WebView2)
//   node desktop-smoke.cjs --url http://127.0.0.1:4173/        (bara sid-/tema-logiken mot ett webbygge, för lokal felsökning)
const { spawn } = require("node:child_process");
const os = require("node:os");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright-core");

const arg = process.argv[2];
const WEB_URL = arg === "--url" ? process.argv[3] : null;
const EXE = WEB_URL ? null : arg;
if (!arg || (arg === "--url" && !WEB_URL)) { console.error("Användning: desktop-smoke.cjs <exe> | --url <url>"); process.exit(2); }
const PORT = 9333; // samma port som i tauri.smoke.conf.json
const failures = [];
const log = (m) => console.log(m);
const check = (ok, what) => { log(`${ok ? "OK  " : "FEL "} ${what}`); if (!ok) failures.push(what); };

const PAGES = [
  { nav: "Hem", h1: /./ },
  { nav: "Resultat", h1: /^Resultat$/ },
  { nav: "Papper", h1: /^Papperportfölj$/ },
  { nav: "Marknad", h1: /^Marknad$/ },
];

async function waitFor(fn, ms, what) {
  const end = Date.now() + ms; let last;
  while (Date.now() < end) { try { const v = await fn(); if (v) return v; } catch (e) { last = e; } await new Promise((r) => setTimeout(r, 500)); }
  throw new Error(`Timeout (${ms} ms): ${what}${last ? ` (${last.message})` : ""}`);
}

// Uppdateringsrutan ("Ny version finns") kan dyka upp när programmet hittar en nyare version i flödet.
// Den får aldrig installera något här: vi stänger bara med det ofarliga valet (Senare/Stäng) och noterar att den visades.
let updateDialogSeen = 0;
async function dismissUpdateDialog(page) {
  for (let i = 0; i < 5; i++) {
    const dlg = page.locator(".overlay .update-dialog");
    if (!(await dlg.count())) return;
    updateDialogSeen++;
    const text = (await dlg.first().innerText()).replace(/\s+/g, " ").trim();
    log(`INFO Uppdateringsrutan visades: "${text.slice(0, 160)}"`);
    const safe = dlg.first().locator("button", { hasText: /^(Senare|Stäng)$/ }).first();
    await safe.click({ timeout: 5000 });
    await page.waitForTimeout(400);
  }
}

// Klick som tål att uppdateringsrutan dyker upp mitt i (den kommer asynkront när uppdateringen är hämtad).
async function safeClick(page, locator) {
  for (let attempt = 0; ; attempt++) {
    await dismissUpdateDialog(page);
    try { await locator.click({ timeout: 4000 }); return; } catch (e) { if (attempt >= 4) throw e; }
  }
}

async function overflow(page) {
  return page.evaluate(() => ({ doc: document.documentElement.scrollWidth, main: (document.querySelector("main") || document.body).scrollWidth, client: document.documentElement.clientWidth }));
}

(async () => {
  let child = null, browser, tmp;
  try {
    let page;
    if (WEB_URL) {
      browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
      page = await (await browser.newContext({ viewport: { width: 1200, height: 800 } })).newPage();
    } else {
      if (!fs.existsSync(EXE)) throw new Error(`Hittar inte programmet: ${EXE}`);
      tmp = fs.mkdtempSync(path.join(os.tmpdir(), "tradergo-smoke-"));
      child = spawn(EXE, [], {
        stdio: ["ignore", "pipe", "pipe"],
        env: { ...process.env, WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS: `--remote-debugging-port=${PORT} --remote-allow-origins=*`, WEBVIEW2_USER_DATA_FOLDER: path.join(tmp, "webview2") },
      });
      let exited = null; child.on("exit", (c) => { exited = c; });
      let out = ""; for (const st of [child.stdout, child.stderr]) st.on("data", (d) => { out = (out + d).slice(-4000); });
      globalThis.__diagnose = () => {
        log(`--- Diagnos: programmet ${exited === null ? "kör fortfarande" : `avslutades med kod ${exited}`}, pid ${child.pid}`);
        log(`--- Programmets utdata (sista 4000 tecknen):\n${out || "(ingen)"}`);
        try { const r = require("node:child_process").execSync(`netstat -ano -p tcp`, { encoding: "utf8" }); log(`--- Lyssnande portar för pid ${child.pid}:\n${r.split(/\r?\n/).filter((l) => /LISTENING/.test(l) && l.trim().endsWith(String(child.pid))).join("\n") || "(inga)"}`); log(`--- Alla lyssnande portar (urval):\n${r.split(/\r?\n/).filter((l) => /LISTENING/.test(l) && /127\.0\.0\.1|\[::1\]/.test(l)).slice(0, 25).join("\n")}`); } catch (e) { log(`netstat misslyckades: ${e.message}`); }
        try { const r = require("node:child_process").execSync(`powershell -NoProfile -Command "Get-Process | Where-Object { $_.ProcessName -match 'trader|msedgewebview2' } | Select-Object Id,ProcessName,MainWindowTitle | Format-Table -AutoSize | Out-String"`, { encoding: "utf8" }); log(`--- Processer:\n${r}`); } catch (e) { log(`Get-Process misslyckades: ${e.message}`); }
      };
      await waitFor(async () => { if (exited !== null) throw new Error(`Programmet avslutades med kod ${exited}`); const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); return r.ok; }, 90000, "WebView2 fjärrfelsökning");
      browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`);
      page = await waitFor(async () => browser.contexts().flatMap((c) => c.pages()).find((p) => /^https?:\/\/tauri\.localhost|^tauri:\/\//.test(p.url())), 60000, "Tauri-fönstret");
    }

    globalThis.__page = page;
    const errors = [];
    page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
    page.on("console", (m) => { if (m.type() === "error") errors.push(`console.error: ${m.text()}`); });
    if (WEB_URL) await page.goto(WEB_URL); else await page.reload();

    await waitFor(() => page.locator("aside nav").first().isVisible(), 30000, "sidomenyn");
    const info = await page.evaluate(() => ({ tauri: typeof window.__TAURI_INTERNALS__ !== "undefined", ua: navigator.userAgent }));
    log(`Webbvy: ${info.ua}`);
    if (!WEB_URL) {
      check(info.tauri, "Körs i Tauri (window.__TAURI_INTERNALS__ finns), alltså skrivbordsläge");
      check(/Edg\//.test(info.ua), "Webbvyn är WebView2 (Edge/Chromium i användaragenten)");
      check(process.platform === "win32", "Körs på Windows");
    }

    // Startintrot (om det visas) stängs med ett klick.
    const intro = page.locator(".intro");
    if (await intro.count()) { await intro.first().click({ timeout: 5000 }).catch(() => {}); await waitFor(async () => (await page.locator(".intro").count()) === 0, 15000, "att introt stängs"); }

    await dismissUpdateDialog(page);
    for (const width of [null, 700]) {
      if (width) { await page.setViewportSize({ width, height: 600 }); await page.waitForTimeout(500); }
      const mode = width ? `${width} px bred` : "normal storlek";
      for (const p of PAGES) {
        const btn = width && width <= 820 ? page.locator("aside button", { hasText: p.nav }).first() : page.locator("aside nav button", { hasText: p.nav }).first();
        await safeClick(page, btn);
        await page.waitForTimeout(600);
        const h1 = (await page.locator("h1").first().innerText()).trim();
        check(p.h1.test(h1) && h1.length > 0, `${p.nav} (${mode}): rubrik "${h1}"`);
        const o = await overflow(page);
        check(o.doc <= o.client && o.main <= o.client, `${p.nav} (${mode}): ingen horisontell overflow (dokument ${o.doc}, main ${o.main}, fönster ${o.client})`);
      }
    }
    // Research Lab och Status ligger under "Mer". Samma kontroller: rubrik och ingen horisontell overflow.
    for (const width of [null, 700]) {
      await page.setViewportSize({ width: width ?? 1200, height: width ? 600 : 800 }); await page.waitForTimeout(500);
      const mode = width ? `${width} px bred` : "normal storlek (1200 px)";
      for (const [label, h1] of [["Research Lab", /^Research Lab$/], ["Status", /^Status$/]]) {
        await safeClick(page, page.locator("aside button.more-btn").first());
        await safeClick(page, page.locator('[role="menuitem"]', { hasText: label }).first());
        await page.waitForTimeout(600);
        const t = (await page.locator("h1").first().innerText()).trim();
        check(h1.test(t), `${label} (${mode}): rubrik "${t}"`);
        const o = await overflow(page);
        check(o.doc <= o.client && o.main <= o.client, `${label} (${mode}): ingen horisontell overflow (dokument ${o.doc}, main ${o.main}, fönster ${o.client})`);
      }
    }
    if (page.viewportSize()) await page.setViewportSize({ width: 1200, height: 800 });
    await page.waitForTimeout(400);

    // Marknad utan marknadsdata (bara skrivbordsläget): tomläget får inte antyda att prisdata finns.
    if (!WEB_URL) {
      await safeClick(page, page.locator("aside nav button", { hasText: "Marknad" }).first());
      await page.waitForTimeout(1500);
      const text = await page.locator("main").innerText();
      log(`INFO Marknad (tomt datalager), text: ${text.replace(/\s+/g, " ").slice(0, 400)}`);
      check(await page.locator(".candle-box, canvas").count() === 0, "Marknad utan data: inget diagram och ingen canvas ritas");
      check(/Ingen marknadsdata att visa/.test(text) || /ingen marknadsdata/i.test(text), "Marknad utan data: tomläget säger att marknadsdata saknas");
      check(!/REALTIDSDATA|HISTORIK/.test(text), "Marknad utan data: inget märke (REALTIDSDATA/HISTORIK) antyder att prisdata finns");
      check(!/\b\d{2,3}[  ]?\d{3},\d\b/.test(text), "Marknad utan data: inga priser visas");
    }

    // Temaväxling: Mer → Utseende. Hem renderar fortfarande efteråt och bakgrunden ändras.
    const themeOf = () => page.evaluate(() => ({ attr: document.documentElement.getAttribute("data-theme"), bg: getComputedStyle(document.body).backgroundColor }));
    const toggle = async () => { await safeClick(page, page.locator("aside button.more-btn").first()); await safeClick(page, page.locator('[role="menuitem"], .item', { hasText: "Utseende" }).first()); await page.mouse.click(700, 400); await page.waitForTimeout(500); };
    const before = await themeOf();
    await toggle(); const dark = await themeOf();
    check(dark.attr === "dark" && dark.bg !== before.bg, `Tema Mörkt: data-theme=${dark.attr}, bakgrund ${before.bg} → ${dark.bg}`);
    for (const p of PAGES) { await safeClick(page, page.locator("aside nav button", { hasText: p.nav }).first()); await page.waitForTimeout(400); const o = await overflow(page); check(o.doc <= o.client, `${p.nav} i mörkt läge: ingen overflow`); }
    await toggle(); const light = await themeOf();
    check(light.attr === "light" && light.bg !== dark.bg, `Tema Ljust: data-theme=${light.attr}, bakgrund ${dark.bg} → ${light.bg}`);
    await safeClick(page, page.locator("aside nav button", { hasText: "Hem" }).first());
    await page.waitForTimeout(400);
    check((await page.locator("h1").first().innerText()).trim().length > 0, "Hem renderar efter temaväxling");

    log(`INFO Uppdateringsrutan visades ${updateDialogSeen} gång(er). Inget installerades.`);
    check(errors.length === 0, `Inga JS-fel (pageerror/console.error): ${errors.length}`);
    for (const e of errors) log(`     ${e}`);
  } catch (e) {
    failures.push(String(e && e.message || e)); log(`FEL  ${e && e.stack || e}`);
    try { globalThis.__diagnose?.(); } catch {}
    try { const t = await globalThis.__page?.locator(".overlay").first().innerText({ timeout: 2000 }); if (t) log(`--- Öppet överlägg: ${t.replace(/\s+/g, " ").slice(0, 300)}`); } catch {}
  } finally {
    try { await browser?.close(); } catch {}
    if (child) { try { child.kill(); } catch {} }
    if (tmp) { try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {} }
  }
  log(failures.length ? `\nRöktestet MISSLYCKADES (${failures.length} fel)` : "\nRöktestet gick igenom");
  process.exit(failures.length ? 1 : 0);
})();
