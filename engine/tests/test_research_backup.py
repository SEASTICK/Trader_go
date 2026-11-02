import gzip
import json

import pytest

from traderlab.research_engine.backup import read_table,snapshot,write_backup,KEYS


def test_pagination_obeys_server_page_cap_and_rejects_repeated_keys():
    class Store:
        def __init__(self):self.calls=[]
        def _get(self,table,query):
            self.calls.append(dict(query))
            return [{'id':'a'}] if len(self.calls)==1 else [{'id':'b'}] if len(self.calls)==2 else []
    store=Store()
    assert read_table(store,'runs')==[{'id':'a'},{'id':'b'}]
    assert store.calls[1]['or']=='(id.gt."a")'
    class Repeated:
        def _get(self,*args):return [{'id':'a'}]
    with pytest.raises(ValueError,match='duplicate'):read_table(Repeated(),'runs')


def test_changed_data_does_not_publish_backup():
    class Store:
        def __init__(self):self.calls=0
        def _get(self,table,query):
            if 'status' in query:return []
            if table=='hypotheses' and 'or' not in query:
                self.calls+=1;return [{'id':str(self.calls)}]
            return []
    with pytest.raises(ValueError,match='changed'):snapshot(Store())


def test_private_compressed_backup_round_trip(tmp_path):
    folder=tmp_path/'backups'
    class Empty:
        def _get(self,*args):return []
    payload=snapshot(Empty())
    path=write_backup(payload,folder)
    assert path.stat().st_mode & 0o777 == 0o600
    assert folder.stat().st_mode & 0o777 == 0o700
    assert json.loads(gzip.decompress(path.read_bytes()))==payload
    assert set(payload['tables'])==set(KEYS)
    assert 'Supabase Auth users/passwords' in payload['excludes']
