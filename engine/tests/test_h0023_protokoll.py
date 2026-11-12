import datetime as dt
import json
import re
from pathlib import Path

from scipy import stats

from traderlab import h0022_coverage as hc
from traderlab.registry import count_attempts, latest_decisions
from traderlab.stats import t_krav

REPO = Path(__file__).resolve().parents[2]
PROTO = (REPO / "research" / "h0023-protokoll.md").read_text(encoding="utf-8")
REG = (REPO / "research" / "registry.md").read_text(encoding="utf-8")
ROWS = json.loads((REPO / "research" / "universe" / "coinm-pit-series.json").read_text(encoding="utf-8"))["series"]


def _row(hid):
    return [l for l in REG.splitlines() if l.startswith(f"| {hid} |")]


def test_kalendertabellen_i_protokollet_är_exakt_rullning_b_ur_universumtabellen():
    cal = hc.cycle_calendar(ROWS, "rullning_b")
    table = []
    for line in PROTO.splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) == 9 and re.fullmatch(r"\d+", c[0]) and re.fullmatch(r"20\d\d-\d\d-\d\d", c[1]):
            table.append(c)
    assert len(cal) == len(table) == 14
    prev_exit = None
    for cy, row in zip(cal, table):
        assert (str(cy["cycle"]), cy["expiry"], cy["decision"], cy["fill"], cy["exit"]) == (row[0], row[1], row[2], row[3], row[4])
        assert int(row[7]) == (dt.date.fromisoformat(cy["exit"]) - dt.date.fromisoformat(cy["fill"])).days
        assert row[8] == ("–" if prev_exit is None else str((dt.date.fromisoformat(cy["fill"]) - dt.date.fromisoformat(prev_exit)).days))
        prev_exit = cy["exit"]
    windows = hc.cycle_windows(cal)
    for cy, row, (a, b) in zip(cal, table, windows):
        assert row[5].startswith(b) and a == cy["fill"]                                 # kolumnen T_k i protokollet är cykelfönstrets slutpunkt
    assert [c["cycle"] for c in cal if c["flat"]] == [2] and (dt.date.fromisoformat(cal[-1]["exit"]) - dt.date.fromisoformat(cal[0]["fill"])).days == 1273


def test_n_23_och_t_gränserna_är_beräknade_och_samma_i_protokoll_och_register():
    assert count_attempts(REG) == 23
    assert round(t_krav(23), 2) == 2.85
    q = stats.t.ppf(1 - 0.05 / 23, 13)
    assert round(q, 2) == 3.45 and q > t_krav(23)
    reg = " ".join(_row("H-0023"))
    for must in ("N=23", "2,85", "3,45", "14 kvartalscykler"):
        assert must in reg
    assert "3,4452" in PROTO and "2,8518" in PROTO and "N = 23" in PROTO
    assert "3,42" not in PROTO and "N = 22" not in PROTO.split("## Läget före registreringen")[1].split("##")[0].replace("H-0023 är ett nytt försök", "")


def test_registerraden_har_14_kolumner_är_registrering_utan_resultat_och_lämnar_h0022_oförändrad():
    rows = _row("H-0023")
    assert len(rows) == 1 and rows[0].count("|") == 14
    cells = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    assert cells[11] == "" and cells[12] == ""                                  # inget resultat och inget beslut
    assert latest_decisions(REG).get("H-0023") is None
    h22 = _row("H-0022")
    assert len(h22) == 2 and h22[1].rstrip().endswith("| OGILTIG |")             # förregistreringen och OGILTIG-raden är oförändrade
    for must in ("kalendern valdes efter", "10 av 13", "OGILTIG", "REJECT", "H-0022"):
        assert must in rows[0] or must in PROTO


def test_protokollet_säger_det_som_ska_sägas_öppet_och_innehåller_inga_resultat():
    for must in ("valdes efter H-0022:s volymdiagnos", "10 av 13 cykler", "kan därför fortfarande bli `OGILTIG`", "H-0020 är `REJECT`",
                 "H-0022 är `OGILTIG` utan körning", "3be2903", "Ingen basis, avkastning, t-statistik eller beta har räknats"):
        assert must in PROTO, must
    results = REPO / "research" / "results"
    assert not any("H-0023" in p.name for p in results.glob("*"))               # ingen resultatfil


def test_statusdokumentet_visar_försöken_och_säger_inte_att_h0016_pågår():
    doc = (REPO / "docs" / "vagen-till-avkastning.md").read_text(encoding="utf-8")
    for must in ("H-0021", "H-0022", "H-0023", "OGILTIG", "förregistrerad men inte körd"):
        assert must in doc, must
    assert "pågår och är inte avgjord" not in doc and "bot/h-0016-tackning" not in doc
    assert "ingen avkastning" in doc.lower() or "Ingen avkastning" in doc


def test_sista_cykelavkastningen_och_btc_använder_slutpunkten_x14_utan_f15_eller_2025_data():
    cal = hc.cycle_calendar(ROWS, "rullning_b")
    win = hc.cycle_windows(cal)
    assert len(win) == 14
    for (a, b), nxt in zip(win, [c["fill"] for c in cal[1:]]):
        assert b == nxt                                                       # T_k = F_{k+1} för cykel 1 till 13
    assert win[-1] == (cal[-1]["fill"], cal[-1]["exit"]) and win[-1][1] == "2024-09-20"      # T_14 = X_14
    assert all(b < "2025-01-01" and b <= "2024-09-20" for _, b in win)
    # syntetiska värden bara på F_1..F_14 och X_14 (inga andra datum, ingen F_15)
    dates = [a for a, _ in win] + [win[-1][1]]
    port = {d: 140000.0 * (1.01 ** i) for i, d in enumerate(dates)}
    btc = {d: 20000.0 * (1.02 ** i) for i, d in enumerate(dates)}
    pairs = hc.paired_observations(win, port, btc)
    assert len(pairs) == 14
    r14, b14 = pairs[-1]
    assert r14 == port["2024-09-20"] / port[cal[-1]["fill"]] - 1 and b14 == btc["2024-09-20"] / btc[cal[-1]["fill"]] - 1
    assert all(abs(r - 0.01) < 1e-12 and abs(b - 0.02) < 1e-12 for r, b in pairs)           # samma intervall för portfölj och BTC
    assert max(dates) == "2024-09-20" and len(set(dates)) == 15                              # 14 inträden + X_14, ingen F_15
    missing = dict(port)
    del missing["2024-09-20"]
    try:
        hc.paired_observations(win, missing, btc)
        raise AssertionError("saknad slutpunkt ska ge KeyError")
    except KeyError:
        pass


def test_protokoll_och_register_låser_slutpunkten_och_btc_kravet():
    for must in ("T_14 = X_14 = 2024-09-20 00:00 UTC", "Ingen `F_15`", "paired_observations", "För beta: en verifierad `BTCUSDT`-spotstapel"):
        assert must in PROTO, must
    assert "F_15" in " ".join(_row("H-0023")) and "2024-09-20 00:00 UTC" in " ".join(_row("H-0023"))
    assert "F_{k+1}` (kontanterna" not in PROTO


def test_gränsen_anges_med_rätt_nämnare_10_av_13_aldrig_10_av_10():
    docs = (REPO / "docs" / "vagen-till-avkastning.md").read_text(encoding="utf-8")
    rapport = (REPO / "research" / "universe" / "rullning-b-rapport.md").read_text(encoding="utf-8")
    for name, text in (("protokoll", PROTO), ("statusdokument", docs), ("rapport", rapport), ("register", " ".join(_row("H-0023")))):
        assert "10 av 10" not in text, name
    assert "10 av 13 cykler** (krav: minst 10 av 13), utan marginal" in PROTO
    assert "10 av 13 kvartal (kravet är minst 10 av 13), utan marginal" in docs
    assert "10 av 13 cykler (krav: minst 10 av 13), utan marginal" in rapport
