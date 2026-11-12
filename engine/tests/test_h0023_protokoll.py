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
        if len(c) == 8 and re.fullmatch(r"\d+", c[0]) and re.fullmatch(r"20\d\d-\d\d-\d\d", c[1]):
            table.append(c)
    assert len(cal) == len(table) == 14
    prev_exit = None
    for cy, row in zip(cal, table):
        assert (str(cy["cycle"]), cy["expiry"], cy["decision"], cy["fill"], cy["exit"]) == (row[0], row[1], row[2], row[3], row[4])
        assert int(row[6]) == (dt.date.fromisoformat(cy["exit"]) - dt.date.fromisoformat(cy["fill"])).days
        assert row[7] == ("–" if prev_exit is None else str((dt.date.fromisoformat(cy["fill"]) - dt.date.fromisoformat(prev_exit)).days))
        prev_exit = cy["exit"]
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
