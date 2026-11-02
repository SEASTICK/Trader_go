"""Retired queue implementation; all jobs must use research_engine.worker.

Direct table PATCH claims bypass the global lease/fencing contract in migration
0003. Keep old imports fail-closed instead of silently starting a second queue.
"""
def _retired(*args, **kwargs):
    raise RuntimeError("Använd traderlab.research_engine.worker med research_claim/research_finish; den äldre jobbkön är avstängd")

claim = execute = process_one = _retired
