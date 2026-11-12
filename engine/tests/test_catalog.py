from pathlib import Path
import pytest
from traderlab.research_engine.catalog import sync_catalog

def test_catalog_copies_only_packaged_registry_and_four_versioned_strategies():
    class Store:
        def __init__(self): self.writes={}
        def _write(self,table,rows,prefer): self.writes[table]=rows
    repo=Path(__file__).resolve().parents[2]
    s=Store(); result=sync_catalog(s,repo)
    # Antalet följer registret: nya hypoteser (H-0013 och framåt) läggs till utan att testet ändras.
    ids={line.split('|')[1].strip() for line in (repo/'research/registry.md').read_text(encoding='utf-8').splitlines()
         if line.startswith('| H-')}
    assert result=={'hypotheses':len(ids),'strategies':4} and len(ids)>=12
    assert set(s.writes)=={'hypotheses','strategies'}
    rows={h['id']:h for h in s.writes['hypotheses']}
    assert all(h['registry_commit'] for h in rows.values())
    # H-0001–H-0012 är avgjorda (REJECT). Senare hypoteser får vara oavgjorda eller ha ett giltigt beslut.
    assert all(rows[f'H-{i:04d}']['decision']=='REJECT' for i in range(1,13))
    assert all(h['decision'] in (None,'REJECT','MORE_RESEARCH','READY_FOR_PAPER','OGILTIG') for h in rows.values())
    assert {s['version'] for s in s.writes['strategies']}=={'1.0.0'}

def test_empty_catalog_fails_before_writing(tmp_path):
    (tmp_path/'research').mkdir();(tmp_path/'research/registry.md').write_text('')
    class Store:
        def _write(self,*a): pytest.fail('An incomplete catalog was written')
    with pytest.raises(ValueError):sync_catalog(Store(),tmp_path)
