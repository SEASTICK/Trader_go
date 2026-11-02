import hashlib
import json
from pathlib import Path
import shutil

import pytest

from traderlab.research_engine.export_registered import export_registered, OUTPUT

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def repo(tmp_path):
    shutil.copytree(ROOT / 'research/results', tmp_path / 'research/results')
    shutil.copytree(ROOT / 'research/audits', tmp_path / 'research/audits')
    shutil.copy2(ROOT / 'research/registry.md', tmp_path / 'research/registry.md')
    (tmp_path / 'app/data').mkdir(parents=True)
    shutil.copy2(ROOT / 'app/data/results.json', tmp_path / 'app/data/results.json')
    return tmp_path


def test_real_results_are_traceable_and_legacy_export_is_unchanged(repo):
    legacy = (repo / 'app/data/results.json').read_bytes()
    rows = export_registered(repo)
    assert [r['hypothesis_id'] for r in rows] == ['H-0009','H-0010','H-0011','H-0012']
    assert (repo / 'app/data/results.json').read_bytes() == legacy
    for r in rows:
        raw = (repo / r['result_file']).read_bytes()
        source = json.loads(raw)
        assert r['stats'] == source['stats'] and r['curves'] == source['curves']
        assert r['trades'] == source['trades'] and r['windows'] == source['windows']
        assert r['decision'] == 'REJECT'
        assert not all(r['criteria'].values())
        assert r['result_sha256'] == hashlib.sha256(raw).hexdigest()
        assert r['audit']['dataset_sha256']
    first = (repo / OUTPUT).read_bytes()
    export_registered(repo)
    assert (repo / OUTPUT).read_bytes() == first


@pytest.mark.parametrize('change', ['simulated', 'holdout', 'criteria'])
def test_invalid_source_cannot_replace_previous_export(repo, change):
    export_registered(repo)
    previous = (repo / OUTPUT).read_bytes()
    p = next((repo / 'research/results').glob('H-0012-*.json'))
    r = json.loads(p.read_text())
    if change == 'simulated':
        r['simulated'] = True
    elif change == 'holdout':
        r['curves']['t'][-1] = '2025-01-01T00:00:00+00:00'
    else:
        r['criteria']['stability_at_least_half'] = 'true'
    p.write_text(json.dumps(r))
    with pytest.raises(ValueError):
        export_registered(repo)
    assert (repo / OUTPUT).read_bytes() == previous


def test_mismatching_audit_is_not_presented_as_verified(repo):
    p = next((repo / 'research/audits').glob('reproduction-*/squeeze_breakout.json'))
    r = json.loads(p.read_text()); r['stats']['sharpe'] += 1
    p.write_text(json.dumps(r))
    assert export_registered(repo)[-1]['audit'] is None


def test_mark_price_report_is_required_before_showing_validation(repo):
    source = ROOT / 'data/audits/fas1-20261102/mark-price/verification.json'
    target = repo / source.relative_to(ROOT)
    target.parent.mkdir(parents=True)
    shutil.copy2(source, target)
    assert all(r['mark_price_audit']['leverage'] == 1 for r in export_registered(repo))
    report = json.loads(target.read_text()); report['results'][0]['possible_hits'] = ['test']
    target.write_text(json.dumps(report))
    assert all(r['mark_price_audit'] is None for r in export_registered(repo))
