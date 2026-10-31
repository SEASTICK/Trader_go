const { invoke } = window.__TAURI__.core;
const { listen } = window.__TAURI__.event;
const $ = (id) => document.getElementById(id);

function showError(err) {
  $("error").textContent = String(err);
  $("error").hidden = !err;
}

function mb(n) {
  return (n / 1048576).toFixed(1) + " MB";
}

function renderUpdate(s) {
  const text = {
    checking: "Checking for updates…",
    none: `You're on the latest version (${s.current}).`,
    available: `Version ${s.version} is available.`,
    downloading: `Downloading ${s.version}…`,
    ready: `Version ${s.version} is downloaded and verified.`,
    error: s.message,
  }[s.state];
  $("update-text").textContent = s.state === "ready" && s.message ? `${text} ${s.message}` : text;
  $("update-text").className = s.state === "error" ? "error" : "muted";

  const p = $("progress");
  p.hidden = s.state !== "downloading";
  if (s.total) { p.max = s.total; p.value = s.downloaded; p.title = `${mb(s.downloaded)} / ${mb(s.total)}`; }
  else p.removeAttribute("value");

  $("notes-box").hidden = !s.notes;
  $("notes").textContent = s.notes || "";
  $("download").hidden = s.state !== "available";
  $("install").hidden = s.state !== "ready";
  $("check").disabled = s.state === "checking" || s.state === "downloading";
}

async function refreshTrades() {
  const rows = await invoke("list_paper_trades");
  $("trades").replaceChildren(...rows.map((t) => {
    const tr = document.createElement("tr");
    for (const v of [t.id, t.opened_at, t.symbol, t.side, t.quantity, t.entry_price]) {
      const td = document.createElement("td");
      td.textContent = v;
      tr.append(td);
    }
    return tr;
  }));
}

function renderActivity(c) {
  $("activity").textContent = `${c.paper} paper session(s), ${c.backtest} backtest(s) running`;
  for (const b of document.querySelectorAll("[data-toggle]")) {
    const running = c[b.dataset.toggle] > 0;
    b.dataset.running = running;
    b.textContent = `${running ? "Stop" : "Start"} ${b.dataset.toggle === "paper" ? "paper session" : "backtest"}`;
  }
}

async function main() {
  const info = await invoke("app_info");
  $("version").textContent = `v${info.version}`;
  $("auto").checked = info.auto_download;
  $("data").textContent = `Data: ${info.data_dir} · schema ${info.schema}`;

  await listen("update-status", (e) => renderUpdate(e.payload));
  renderUpdate(await invoke("update_status"));
  renderActivity({ paper: 0, backtest: 0 });
  await refreshTrades();

  $("check").onclick = () => invoke("check_for_update").catch(showError);
  $("download").onclick = () => invoke("download_update").catch(showError);
  $("install").onclick = () => invoke("install_update").then(() => showError(""), showError);
  $("auto").onchange = (e) => invoke("set_setting", { key: "auto_download", value: String(e.target.checked) }).catch(showError);

  for (const b of document.querySelectorAll("[data-toggle]")) {
    b.onclick = async () => {
      const cmd = b.dataset.running === "true" ? "stop_activity" : "start_activity";
      renderActivity(await invoke(cmd, { kind: b.dataset.toggle }));
    };
  }

  $("trade").onsubmit = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    try {
      await invoke("add_paper_trade", {
        symbol: f.get("symbol"), side: f.get("side"),
        quantity: Number(f.get("quantity")), entryPrice: Number(f.get("price")),
      });
      e.target.reset();
      showError("");
      await refreshTrades();
    } catch (err) { showError(err); }
  };
}

main().catch(showError);
