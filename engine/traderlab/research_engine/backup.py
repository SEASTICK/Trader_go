"""Private research-table export. Supplements provider backups; excludes Supabase Auth."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path

from .supabase import SupabaseStore

KEYS = {'candles':('provider','market','symbol','interval','open_time'),
        'funding_rates':('symbol','funding_time'), 'strategies':('name','version'),
        'hypotheses':('id',), 'research_members':('user_id',), 'runs':('id',),
        'run_results':('run_id',), 'run_trades':('run_id','n')}


def encoded(tables):
    return json.dumps(tables,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def read_table(store,table):
    keys=KEYS[table]
    query={'select':'*','order':','.join(k+'.asc' for k in keys),'limit':500}
    rows=[]; seen=set()
    while True:
        page=store._get(table,query)
        if not page:
            return rows
        for row in page:
            key=tuple(row[k] for k in keys)
            if key in seen:
                raise ValueError('Backup pagination contains duplicate keys')
            seen.add(key)
        rows.extend(page)
        last=page[-1]
        def literal(value):
            return '"'+str(value).replace('\\','\\\\').replace('"','\\"')+'"'
        choices=[]
        for i,key in enumerate(keys):
            terms=[f'{k}.eq.{literal(last[k])}' for k in keys[:i]]
            terms.append(f'{key}.gt.{literal(last[key])}')
            choices.append(terms[0] if len(terms)==1 else 'and('+','.join(terms)+')')
        query['or']='('+','.join(choices)+')'


def snapshot(store):
    # REST has no cross-request transaction. Refuse active jobs and require two
    # identical full reads. Explicitly do not label this a transactional pg_dump.
    if store._get('runs',{'select':'id','status':'eq.running','limit':1}):
        raise ValueError('Research job active; keep previous backup and retry later')
    first={table:read_table(store,table) for table in KEYS}
    second={table:read_table(store,table) for table in KEYS}
    if encoded(first)!=encoded(second):
        raise ValueError('Research data changed during export; no backup published')
    if store._get('runs',{'select':'id','status':'eq.running','limit':1}):
        raise ValueError('Research job started during export; no backup published')
    return {'contract_version':1,'captured_at':datetime.now(timezone.utc).isoformat(),
            'consistency':'two matching REST reads; not a transactional database backup',
            'excludes':['Supabase Auth users/passwords','Storage objects','credentials','volatile worker slot'],
            'tables_sha256':hashlib.sha256(encoded(second)).hexdigest(),'tables':second}


def write_backup(payload,folder):
    folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    if folder.stat().st_mode & 0o077:
        raise ValueError('Backup directory must be private (0700)')
    name='research-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json.gz'
    target=folder/name; temporary=folder/(name+'.partial')
    raw=gzip.compress(encoded(payload),mtime=0)
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    # Verify decompression and content before publishing a completed filename.
    restored=json.loads(gzip.decompress(temporary.read_bytes()))
    if hashlib.sha256(encoded(restored['tables'])).hexdigest()!=payload['tables_sha256']:
        raise ValueError('Backup read-back verification failed')
    temporary.replace(target)
    return target


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env-file',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    payload=snapshot(SupabaseStore.from_env_file(a.env_file))
    path=write_backup(payload,a.output)
    print(json.dumps({'backup_file':path.name,'tables_sha256':payload['tables_sha256'],
                      'counts':{k:len(v) for k,v in payload['tables'].items()},
                      'verified_readback':True,'full_supabase_backup':False}))


if __name__=='__main__': main()
