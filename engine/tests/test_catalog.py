from pathlib import Path
import pytest
from traderlab.research_engine.catalog import sync_catalog

def test_catalog_copies_only_packaged_registry_and_four_versioned_strategies():
    class Store:
        def __init__(self): self.writes={}
        def _write(self,table,rows,prefer): self.writes[table]=rows
    s=Store(); result=sync_catalog(s,Path(__file__).resolve().parents[2])
    assert result=={'hypotheses':12,'strategies':4}
    assert set(s.writes)=={'hypotheses','strategies'}
    assert all(h['registry_commit'] and h['decision']=='REJECT' for h in s.writes['hypotheses'])
    assert {s['version'] for s in s.writes['strategies']}=={'1.0.0'}

def test_empty_catalog_fails_before_writing(tmp_path):
    (tmp_path/'research').mkdir();(tmp_path/'research/registry.md').write_text('')
    class Store:
        def _write(self,*a): pytest.fail('An incomplete catalog was written')
    with pytest.raises(ValueError):sync_catalog(Store(),tmp_path)
