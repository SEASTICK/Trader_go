#!/usr/bin/env python3
"""Reproduce the A2 registration/provenance review; no market-history reads."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'engine'))
from traderlab import registry, stats

REV = 'db7f83b56e79f8a76b5e0d297be4503170070c0f'
BASE = '0cbc32b'
TARGET = Path(__file__).with_name('verification.json')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True)


def run():
    assert git('merge-base', '--is-ancestor', BASE, REV) == ''
    changed = set(git('diff', '--name-only', BASE, REV).splitlines())
    assert changed == {'research/h0017-protokoll.md', 'research/registry.md',
                       'docs/momentum-status.json', 'docs/momentum-checklista.md'}
    original = git('show', 'a25db81:docs/momentum-protokoll-A1.md')
    final = (ROOT / 'research/h0017-protokoll.md').read_text()
    assert final == git('show', REV + ':research/h0017-protokoll.md')
    body = original[original.index('## 1. Metodtabell'):]
    expected = re.sub(r'\]\((?!\.\./)([^)]+)\)', lambda m: '](../docs/' + m.group(1) + ')', body)
    assert final[final.index('## 1. Metodtabell'):] == expected
    links = re.findall(r'\]\(([^)]+)\)', final)
    assert all((ROOT / 'research' / link).exists() for link in links)

    before = git('show', BASE + ':research/registry.md')
    after = git('show', REV + ':research/registry.md')
    assert (ROOT / 'research/registry.md').read_text() == after
    assert after.startswith(before)
    added = after[len(before):].splitlines()
    assert len(added) == 1 and added[0].startswith('| H-0017 |')
    assert len(added[0].strip('|').split('|')) == 13
    assert 'H-0017' not in registry.ids_in(before)
    assert registry.count_attempts(before) == 16 and registry.count_attempts(after) == 17
    registered = registry.require_registered('H-0017', ROOT)
    assert registered.registry_commit == REV and registered.attempts == 17
    t = max(2.67, stats.t_krav(17))
    assert math.isclose(t, 2.754268270633685, abs_tol=1e-14, rel_tol=0)

    prior = json.loads((ROOT / 'research/audits/momentum-a1-a25db81/verification.json').read_text())
    for path, digest in prior['source_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    for path in ['docs/momentum-a1-granskning-cb335ee.md', 'docs/momentum-a1-granskning-979fb30.md',
                 'docs/momentum-a1-granskning-a25db81.md']:
        assert (ROOT / path).read_text() == git('show', BASE + ':' + path)
    source_hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in
                     ('research/h0017-protokoll.md', 'research/registry.md')}
    return {'reviewed_revision': REV, 'diff_base': BASE, 'hypothesis_id': 'H-0017',
            'method_body_unchanged_after_link_relocation': True, 'valid_local_links': len(links),
            'previous_register_bytes_preserved': True, 'appended_rows': 1, 'columns': 13,
            'registration_commit': registered.registry_commit, 'N': registered.attempts,
            't_requirement': t, 'N_sok': 12 + 1120 + 81, 'source_sha256': source_hashes,
            'market_history_read': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result, 'A2 registration/provenance changed'
        print('PASS: H-0017 committed gate, append-only register, unchanged method, links and locked counts')
    else:
        TARGET.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        print(TARGET)
