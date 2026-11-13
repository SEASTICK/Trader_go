"""Fryst känslighetskontroll: parametrar oförändrade, bara 2020-2022 läses, registret rörs inte. Syntetisk data."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from traderlab.agentlab import data, sensitivity
from traderlab.agentlab.data import synthetic_panel
from traderlab.agentlab.strategies import make_spec

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "research" / "agentlab"
FROZEN_KEYS = {"610bac07a444": "ensemble_rank", "0051738937c5": "ml_xs", "2d3d4d5026e5": "ensemble_rank", "108fb9dfbab8": "bab"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_de_fyra_registrerade_specifikationerna_är_oförändrade():
    cands = sensitivity.frozen_candidates(ROOT)
    assert {c["key"]: c["family"] for c in cands} == FROZEN_KEYS
    for c in cands:
        assert make_spec(c["family"], c["parameters"])["key"] == c["key"]          # samma parametrar ger samma nyckel
        assert c["old"]["n"] == 822


def test_ändrade_parametrar_avvisas(tmp_path):
    rows = (ROOT / "experiments.jsonl").read_text(encoding="utf-8").splitlines()
    changed = []
    for line in rows:
        r = json.loads(line)
        if r["stage"] == "final" and r["key"] == "610bac07a444":
            r["parameters"] = {**r["parameters"], "q": 0.25}
        changed.append(json.dumps(r, ensure_ascii=False))
    (tmp_path / "experiments.jsonl").write_text("\n".join(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="oförändrad"):
        sensitivity.frozen_candidates(tmp_path)


def test_panel_med_data_efter_2022_vägras():
    p = synthetic_panel(n_days=1500, n_assets=22, seed=3)                            # 2020-01-01 + 1500 dagar = in i 2024
    with pytest.raises(ValueError, match="2020-2022"):
        sensitivity.evaluate(p, make_spec("bab", {"vt": 0.2, "k": 60, "q": 0.3, "rebal": 7, "uni": 50}), None)


def test_load_um_panel_end_öppnar_inga_arkiv_från_2023(monkeypatch, tmp_path):
    seen = []

    def fake_load(market, sym, interval, data_dir, start=None, end=None):
        seen.append(("kl", sym, end))
        idx = pd.date_range("2020-01-01", "2022-12-31", freq="D", tz="UTC")
        return pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}, index=idx)

    def fake_funding(sym, data_dir, start=None, end=None):
        seen.append(("fu", sym, end))
        return pd.Series(0.0001, index=pd.date_range("2020-01-01", "2022-12-31 16:00", freq="8h", tz="UTC"))

    from traderlab.data import binance
    monkeypatch.setattr(binance, "load", fake_load)
    monkeypatch.setattr(binance, "load_funding", fake_funding)
    panel = data.load_um_panel(tmp_path, symbols=["AUSDT", "BUSDT", "AUSDT_221230"], end=pd.Timestamp("2023-01-01", tz="UTC"))
    assert seen and all(e == pd.Timestamp("2023-01-01", tz="UTC") for _, _, e in seen)      # varje anrop begränsas till före 2023
    assert panel.close.index.max() <= pd.Timestamp("2022-12-31", tz="UTC")
    assert panel.symbols == ["AUSDT", "BUSDT"]                                               # leveranskontrakt läses inte


def test_körning_på_syntetisk_panel_skriver_bara_i_utdatamappen_och_rör_inte_registret(tmp_path):
    p = synthetic_panel(n_days=900, n_assets=24, seed=5, momentum=0.4)
    files = [ROOT / "experiments.jsonl", ROOT / "state.json", REPO / "research" / "registry.md"]
    before = [sha(f) for f in files]
    cands = [c for c in sensitivity.frozen_candidates(ROOT) if c["family"] in ("ensemble_rank", "bab")]
    out = tmp_path / "out"
    out.mkdir()
    rep = sensitivity.run_sensitivity(tmp_path, ROOT, out, panel=p, old_symbols=p.symbols[:12], candidates=cands)
    assert [sha(f) for f in files] == before
    assert sorted(x.name for x in out.iterdir()) == ["frozen-r001-r004.json", "frozen-r001-r004.md"]
    assert len(rep["candidates"]) == 3 and rep["unchanged_parameters_checked"] is True
    c = rep["candidates"][0]
    for step in ("step_B_old_perps_new_rules", "step_C_full_panel_new_rules"):
        assert c[step]["status"] in ("GILTIG", "OGILTIG") and "sharpe" in c[step] and "t" in c[step] and "sharpe_cost_2_5x" in c[step]
        assert c[step]["universe"]["mean_eligible_per_day"] > 0
    assert "EFTERHANDSDIAGNOSTIK" in (out / "frozen-r001-r004.md").read_text(encoding="utf-8")


def test_överlever_kräver_giltig_täckning_och_alla_trösklar():
    ok = {"status": "GILTIG", "sharpe": 1.2, "t": 2.2, "sharpe_cost_2_5x": 0.4}
    assert sensitivity.survives(ok)
    assert not sensitivity.survives({**ok, "status": "OGILTIG"})
    assert not sensitivity.survives({**ok, "t": 1.9})
    assert not sensitivity.survives({**ok, "sharpe_cost_2_5x": 0.0})
    assert not sensitivity.survives({"status": "EJ KÖRBAR"})
