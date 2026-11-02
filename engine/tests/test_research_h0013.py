"""H-0013 som registrerat jobb i workern (K1–K12) på syntetiska frysta arkiv. Inget moln, ingen riktig data."""
import hashlib
import io
import json
import zipfile
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from traderlab import fas2, fas2_eval
from traderlab.data import binance
from traderlab.research_engine import h0013, worker
from traderlab.synthetic import make_bars

UTC = lambda t: pd.Timestamp(t, tz="UTC")
MONTHS = pd.period_range("2020-01", "2024-12", freq="M")


def job(**over):
    base = {"id": "run-1", "lease_token": "tok", "attempts": 1, **h0013.EXPECTED,
            "period_start": "2020-01-01T00:00:00+00:00", "period_end": "2025-01-01T00:00:00+00:00"}
    return {**base, **over}


def _zip(name: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name.replace(".zip", ".csv"), text)
    return buf.getvalue()


def _write(folder, name, text):
    raw = _zip(name, text)
    (folder / name).write_bytes(raw)
    (folder / (name + ".CHECKSUM")).write_text(f"{hashlib.sha256(raw).hexdigest()}  {name}\n")
    return raw


@pytest.fixture(scope="module")
def frozen(tmp_path_factory):
    """Syntetiska Binance-arkiv 2020–2024 (60 + 60), plus ett slutprovsarkiv som aldrig får öppnas."""
    root = tmp_path_factory.mktemp("data")
    bars = make_bars(int((UTC("2025-01-01") - UTC("2020-01-01")) / pd.Timedelta(hours=4)), seed=1, vol=0.015)
    folders = h0013._folders(root)
    for f in folders.values():
        f.mkdir(parents=True)
    files = []
    for m in MONTHS:
        part = bars[(bars.index >= UTC(m.start_time)) & (bars.index < UTC((m + 1).start_time))]
        rows = "\n".join(f"{int(t.value // 10**6)}," + ",".join(repr(float(r[c])) for c in ("open", "high", "low", "close", "volume"))
                         for t, r in part.iterrows())
        name = f"BTCUSDT-4h-{m}.zip"
        files.append({"name": name, "sha256": hashlib.sha256(_write(folders["4h"], name, rows)).hexdigest()})
        times = pd.date_range(UTC(m.start_time), UTC((m + 1).start_time), freq="8h", inclusive="left")
        frows = "\n".join(f"{int(t.value // 10**6)},8,0.0001" for t in times)
        fname = f"BTCUSDT-fundingRate-{m}.zip"
        files.append({"name": fname, "sha256": hashlib.sha256(_write(folders["fundingRate"], fname, frows)).hexdigest()})
    # Slutprovets arkiv ligger i samma mapp men är trasigt: öppnas det märks det direkt.
    (folders["4h"] / "BTCUSDT-4h-2025-01.zip").write_bytes(b"holdout must never be opened")
    (folders["fundingRate"] / "BTCUSDT-fundingRate-2025-01.zip").write_bytes(b"holdout must never be opened")
    loaded_bars, loaded_funding = fas2.load_development(root)
    manifest = {"files": files,
                "bars_sha256": hashlib.sha256(loaded_bars.to_csv(float_format="%.17g").encode()).hexdigest(),
                "funding_sha256": hashlib.sha256(loaded_funding.to_csv(float_format="%.17g").encode()).hexdigest()}
    return root, manifest


# Kontraktet (K3)

def test_the_exact_contract_is_accepted():
    h0013.validate(job())


@pytest.mark.parametrize("field, value", [
    ("kind", "exploration"), ("hypothesis_id", "H-0012"), ("strategy", "ema_adx_trend"),
    ("version", "h0013-evaluation/2.0.0"), ("market", "spot"), ("symbol", "ETHUSDT"), ("interval", "1h"),
    ("params", {"protocol": "research/fas2-protokoll.md", "n_permutations": 20, "playbooks": 81}),
    ("params", {"protocol": "research/fas2-protokoll.md", "n_permutations": 200, "playbooks": 81, "x": 1}),
    ("capital", 50000), ("costs", {"fee_bps": 0, "spread_bps": 2, "slippage_bps": 5}),
    ("period_end", "2025-01-02T00:00:00+00:00"), ("period_end", "2026-09-30T00:00:00+00:00"),
    ("period_start", "2019-12-01T00:00:00+00:00"), ("period_start", "2020-01-01T00:00:00"),
])
def test_any_deviation_from_the_contract_is_rejected(field, value):
    with pytest.raises(ValueError):
        h0013.validate(job(**{field: value}))


def test_contract_matches_the_migration():
    sql = (h0013.REPO / "supabase/migrations/0005_h0013_queue.sql").read_text()
    assert "'h0013_adaptive_playbook', 'h0013-evaluation/1.0.0'" in sql
    assert '"n_permutations":200,"playbooks":81' in sql and h0013.DATASET in sql
    assert h0013.EXPECTED["version"] == fas2_eval.EVALUATION_VERSION


# Frysta arkiv (K10)

def test_verified_archives_load_and_match_the_frozen_values(frozen, monkeypatch):
    root, manifest = frozen
    opened = []
    orig = type(root).read_bytes

    def spy(self):
        opened.append(self.name)
        return orig(self)
    monkeypatch.setattr(type(root), "read_bytes", spy)
    bars, funding = h0013.load_frozen(root, manifest)
    assert bars.index.max() < UTC("2025-01-01") and funding.index.max() < UTC("2025-01-01")
    assert not [n for n in opened if "2025" in n], "holdout archives are never opened"
    first_load = opened.index(next(n for n in opened if n.endswith(".zip")))
    verified = {f["name"] for f in manifest["files"]}
    assert set(opened[first_load:first_load + 120]) <= verified | {n + ".CHECKSUM" for n in verified}


@pytest.mark.parametrize("damage", ["changed", "rewritten", "missing", "extra", "checksum", "no_checksum"])
def test_archive_problems_are_found_before_any_data_is_loaded(frozen, tmp_path, monkeypatch, damage):
    root, manifest = frozen
    import shutil
    copy = tmp_path / "data"
    shutil.copytree(root, copy)
    f4 = h0013._folders(copy)["4h"]
    if damage == "changed":
        (f4 / "BTCUSDT-4h-2022-03.zip").write_bytes(_zip("BTCUSDT-4h-2022-03.zip", "1,2,3,4,5,6"))
    elif damage == "rewritten":
        # Arkivet och dess CHECKSUM är omskrivna och stämmer med varandra, men inte med manifestet.
        _write(f4, "BTCUSDT-4h-2022-03.zip", "1,2,3,4,5,6")
    elif damage == "missing":
        (f4 / "BTCUSDT-4h-2023-07.zip").unlink()
    elif damage == "extra":
        # Ett arkiv inom perioden som manifestet inte känner till.
        manifest = {**manifest, "files": [f for f in manifest["files"] if f["name"] != "BTCUSDT-4h-2024-06.zip"]}
    elif damage == "checksum":
        (f4 / "BTCUSDT-4h-2021-01.zip.CHECKSUM").write_text("0" * 64 + "\n")
    else:
        (f4 / "BTCUSDT-4h-2021-01.zip.CHECKSUM").unlink()
    monkeypatch.setattr(fas2, "load_development", lambda *a, **k: pytest.fail("data loaded before verification"))
    with pytest.raises(ValueError):
        h0013.load_frozen(copy, manifest)


def test_archives_outside_the_development_period_are_never_opened(frozen, tmp_path, monkeypatch):
    root, manifest = frozen
    import shutil
    copy = tmp_path / "data"
    shutil.copytree(root, copy)
    (h0013._folders(copy)["4h"] / "BTCUSDT-4h-2019-12.zip").write_bytes(b"before 2020 must never be opened")
    opened = []
    orig = type(copy).read_bytes
    monkeypatch.setattr(type(copy), "read_bytes", lambda self: (opened.append(self.name), orig(self))[1])
    h0013.load_frozen(copy, manifest)
    assert not [n for n in opened if "2019" in n or "2025" in n]


def test_loaded_values_must_match_the_manifest_hashes(frozen):
    root, manifest = frozen
    with pytest.raises(ValueError, match="Staplarna"):
        h0013.load_frozen(root, {**manifest, "bars_sha256": "0" * 64})
    with pytest.raises(ValueError, match="Finansieringsräntan"):
        h0013.load_frozen(root, {**manifest, "funding_sha256": "0" * 64})


# Hela jobbet i beräkningsprocessen (K6, K11, K12)

@pytest.fixture
def quick(monkeypatch, frozen):
    """Samma kod, men med 2 permutationer och 2 spelböcker så att testet går snabbt."""
    root, manifest = frozen
    monkeypatch.setattr(h0013, "MANIFEST", root / "manifest.json")
    (root / "manifest.json").write_text(json.dumps(manifest))
    orig = fas2_eval.evaluate
    from traderlab import adaptive
    monkeypatch.setattr(fas2_eval, "evaluate",
                        lambda *a, **k: orig(*a, **{**k, "n_permutations": 2, "playbooks": adaptive.all_playbooks()[:2]}))
    monkeypatch.setenv("TRADERGO_REVISION", "abc1234")
    return root, manifest


def test_run_job_writes_a_strict_result_and_records_the_attempt(quick, tmp_path):
    root, manifest = quick
    out = tmp_path / "result.json"
    h0013.run_job(job(), root, out)
    payload = json.loads(out.read_text())
    assert payload["mode"] == "registered" and payload["hypothesis_id"] == "H-0013"
    assert payload["evaluation_version"] == "h0013-evaluation/1.0.0" and payload["status"] == "completed"
    assert payload["decision"] in ("REJECT", "MORE_RESEARCH") and len(payload["criteria"]) == 5
    assert payload["dataset_sha256"] == h0013.DATASET and payload["holdout_loaded"] is False
    assert isinstance(payload["stats"], dict) and isinstance(payload["curves"], dict)
    assert payload["revision"] == {"commit": "abc1234", "source": "TRADERGO_REVISION"}
    assert len(payload["data"]["sha256"]) == 64 and payload["attempt"] == 1
    assert all(set(t) == {"side", "entry_time", "exit_time", "entry_price", "exit_price", "net_return", "exit_reason"}
               for t in payload["trades"])
    saved = list((root / "h0013-attempts").glob("H-0013-*-completed.json"))
    assert saved and json.loads(saved[-1].read_text())["decision"] == payload["decision"]
    assert float(out.with_suffix(".progress").read_text()) == pytest.approx(0.95)


def test_failed_job_keeps_partial_results_without_a_decision(quick, tmp_path, monkeypatch):
    root, _ = quick
    monkeypatch.setattr(fas2_eval, "regime_results", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stopp")))
    with pytest.raises(RuntimeError):
        h0013.run_job(job(id="run-2", attempts=2), root, tmp_path / "result.json")
    saved = sorted((root / "h0013-attempts").glob("H-0013-*-aborted.json"))
    body = json.loads(saved[-1].read_text())
    assert body["status"] == "aborted" and "decision" not in body and body["attempt"] == 2
    assert body["steps"]["walk_forward"] == "done" and body["steps"]["regimes"] == "incomplete"
    assert "h0013" in body and "comparisons" in body and len(body["data"]["sha256"]) == 64
    assert not (tmp_path / "result.json").exists(), "nothing is published"


def test_invalid_job_is_refused_before_any_file_is_read(quick, tmp_path, monkeypatch):
    root, _ = quick
    monkeypatch.setattr(h0013, "load_frozen", lambda *a, **k: pytest.fail("data read for an invalid job"))
    with pytest.raises(ValueError):
        h0013.run_job(job(capital=1), root, tmp_path / "r.json")


# Workern (K5, K9)

def test_worker_routes_h0013_to_its_runner_with_a_two_hour_timeout(monkeypatch, tmp_path):
    assert worker.timeout_for(job()) == 7200
    assert worker.timeout_for({"kind": "registered", "hypothesis_id": "H-0009"}) == 1800
    assert worker.timeout_for({"kind": "exploration"}) == 1800
    seen = []
    monkeypatch.setattr(h0013, "run_job", lambda j, d, o: seen.append(("h0013", j["hypothesis_id"])))
    from traderlab.research_engine import registered
    monkeypatch.setattr(registered, "run_job", lambda j, d, o: seen.append(("fas1", j["hypothesis_id"])))
    worker.child(job(), str(tmp_path), str(tmp_path / "o.json"))
    worker.child({**job(), "hypothesis_id": "H-0009"}, str(tmp_path), str(tmp_path / "o.json"))
    assert seen == [("h0013", "H-0013"), ("fas1", "H-0009")]


def test_child_failure_for_h0013_reports_the_error_without_server_key(monkeypatch, tmp_path):
    monkeypatch.setattr(h0013, "run_job", lambda *a: (_ for _ in ()).throw(ValueError("Arkiven matchar inte")))
    with pytest.raises(SystemExit):
        worker.child(job(), str(tmp_path), str(tmp_path / "o.json"))
    assert (tmp_path / "o.error").read_text() == "Arkiven matchar inte"


class FakeProcess:
    def __init__(self, finish_after=None, exitcode=0):
        self.alive, self.stopped, self.exitcode, self.ticks, self.finish_after = True, False, exitcode, 0, finish_after

    def start(self):
        pass

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.alive, self.stopped = False, True

    def kill(self):
        self.terminate()

    def join(self, timeout):
        self.ticks += 1
        if self.finish_after is not None and self.ticks >= self.finish_after:
            self.alive = False


def test_restart_after_lost_lease_reruns_and_only_the_current_token_publishes(monkeypatch, tmp_path):
    """Workern startar om: andra försöket får ny token; det gamla försökets publicering avvisas av databasen."""
    published = []

    class Store:
        def __init__(self, token):
            self.token = token

        def rpc(self, name, params):
            if name == "research_heartbeat":
                return "running"
            if name == "research_finish":
                ok = params["p_token"] == "new" and not published
                if ok:
                    published.append(params["p_id"])
                return ok

    def fake_process(result_ok):
        def factory(target, args):
            j, data_dir, output = args
            from pathlib import Path
            Path(output).write_text(json.dumps({"mode": "registered", "hypothesis_id": "H-0013"}))
            return FakeProcess(finish_after=1)
        return factory
    monkeypatch.setattr(worker.mp, "get_context", lambda _: SimpleNamespace(Process=fake_process(True)))
    worker.execute(Store("old"), job(lease_token="old", attempts=1), tmp_path, lambda: False, timeout=7200)
    worker.execute(Store("new"), job(lease_token="new", attempts=2), tmp_path, lambda: False, timeout=7200)
    worker.execute(Store("new"), job(lease_token="new", attempts=2), tmp_path, lambda: False, timeout=7200)
    assert published == ["run-1"], "exactly one result is published, by the current lease"


@pytest.mark.parametrize("state, finishes", [("cancelled", True), ("lost", False)])
def test_cancel_or_lost_lease_stops_the_h0013_child(monkeypatch, tmp_path, state, finishes):
    process = FakeProcess()
    monkeypatch.setattr(worker.mp, "get_context", lambda _: SimpleNamespace(Process=lambda **_: process))
    calls = []

    class Store:
        def rpc(self, name, params):
            calls.append((name, params))
            return state if name == "research_heartbeat" else True
    worker.execute(Store(), job(), tmp_path, lambda: False, timeout=7200)
    assert process.stopped
    finish = [p for n, p in calls if n == "research_finish"]
    assert bool(finish) is finishes and all("p_result" not in p for p in finish)


def test_timeout_stops_the_h0013_child_and_fails_the_run(monkeypatch, tmp_path):
    process = FakeProcess()
    monkeypatch.setattr(worker.mp, "get_context", lambda _: SimpleNamespace(Process=lambda **_: process))
    calls = []

    class Store:
        def rpc(self, name, params):
            calls.append((name, params))
            return True
    worker.execute(Store(), job(), tmp_path, lambda: False, timeout=-1)
    assert process.stopped and calls[0][0] == "research_finish" and "tidsgräns" in calls[0][1]["p_error"]
