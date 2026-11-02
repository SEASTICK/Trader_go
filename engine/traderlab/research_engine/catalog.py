"""Mirror the packaged Git registry; only source-controlled decisions are copied."""
from pathlib import Path
from ..server.registry_sync import parse_registry
from ..strategies.rules import SPECS

def sync_catalog(store,repo:Path):
    hypotheses=parse_registry((repo/'research/registry.md').read_text(encoding='utf-8'))
    if len(hypotheses)<12 or any(not h['registry_commit'] for h in hypotheses):
        raise ValueError('Det paketerade registret är ofullständigt')
    store._write('hypotheses',hypotheses,'resolution=merge-duplicates,return=minimal')
    strategies=[dict(name=s.name,version=s.version,description=s.description,defaults=s.defaults,
                    space={k:vars(v) for k,v in s.space.items()}) for s in SPECS.values()]
    store._write('strategies',strategies,'resolution=merge-duplicates,return=minimal')
    return dict(hypotheses=len(hypotheses),strategies=len(strategies))
