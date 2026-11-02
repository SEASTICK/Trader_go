// npm install --prefix /tmp/tradergo-pg-test @electric-sql/pglite
// PGLITE_MODULE=/tmp/tradergo-pg-test/node_modules/@electric-sql/pglite/dist/index.js node scripts/test-research-queue.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite');
const db = new PGlite();
const member = '00000000-0000-4000-8000-000000000001';
const outsider = '00000000-0000-4000-8000-000000000002';
await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
  create schema auth; create table auth.users(id uuid primary key);
  create function auth.uid() returns uuid language sql stable as
  $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
  grant usage on schema public,auth to anon,authenticated,service_role;
  grant execute on function auth.uid() to public;
  insert into auth.users values ('${member}'),('${outsider}');`);
for (const name of ['0001_research.sql','0002_research_members.sql','0003_research_queue.sql','0004_registered_reproduction.sql']) {
  await db.exec(readFileSync(new URL('../supabase/migrations/' + name, import.meta.url), 'utf8'));
}
await db.query('insert into research_members(user_id) values ($1)', [member]);
async function role(name, uid='') {
  await db.exec('reset role');
  await db.query("select set_config('request.jwt.claim.sub',$1,false)",[uid]);
  await db.exec('set role '+name);
}
const request = { request_key:'10000000-0000-4000-8000-000000000001',strategy:'ema_adx_trend',market:'spot',interval:'4h',
  period_start:'2022-01-01T00:00:00Z',period_end:'2022-03-01T00:00:00Z',params:{} };
const enqueue = async r => (await db.query('select research_enqueue($1::jsonb) as id',[JSON.stringify(r)])).rows[0].id;
await role('anon');
await assert.rejects(db.query('select * from runs'), /permission denied/);
await assert.rejects(enqueue(request), /permission denied/);
await role('authenticated',outsider);
assert.equal((await db.query('select * from research_members')).rows.length,0);
await assert.rejects(enqueue(request), /Medlemsåtkomst/);
await role('authenticated',member);
assert.equal((await db.query('select * from research_members')).rows.length,1);
await assert.rejects(db.query("insert into runs(kind) values ('exploration')"), /permission denied/);
await assert.rejects(db.query("update runs set status='cancelled'"), /permission denied/);
await assert.rejects(db.query('insert into research_members(user_id) values ($1)',[outsider]), /permission denied/);
await assert.rejects(db.query("select research_claim('bad')"), /permission denied/);
await assert.rejects(enqueue({...request,period_end:'2026-01-01'}), /Perioden/);
const id=await enqueue(request);
assert.equal(await enqueue(request),id);
await role('authenticated',outsider);
assert.equal((await db.query('select * from runs')).rows.length,0);
await role('service_role');
const claim = async () => (await db.query("select research_claim('test-worker') as job")).rows[0].job;
const first=await claim(); assert.equal(first.id,id);
assert.equal(await claim(),null);
await role('authenticated',member);
assert.equal((await db.query('select research_cancel($1) as ok',[id])).rows[0].ok,true);
await role('service_role');
assert.equal(await claim(),null); // cancelled process still owns slot
assert.equal((await db.query('select research_heartbeat($1,$2,0.2) as state',[id,first.lease_token])).rows[0].state,'cancelled');
assert.equal((await db.query('select research_finish($1,$2,null,$3) as ok',[id,first.lease_token,'cancelled'])).rows[0].ok,true);
await role('authenticated',member);
const id2=await enqueue({...request,request_key:'10000000-0000-4000-8000-000000000002'});
await role('service_role'); const second=await claim(); assert.equal(second.id,id2);
await db.exec("update research_worker_slot set expires_at=clock_timestamp()-interval '1 second'");
const retry=await claim(); assert.equal(retry.id,id2); assert.equal(retry.attempts,2);
assert.notEqual(retry.lease_token,second.lease_token);
assert.equal((await db.query('select research_finish($1,$2,null,$3) as ok',[id2,second.lease_token,'stale'])).rows[0].ok,false);
const result={mode:'exploration',stats:{net_return:0.1},curves:{t:[],equity:[],drawdown:[]},trades:[]};
assert.equal((await db.query('select research_finish($1,$2,$3::jsonb,null) as ok',[id2,retry.lease_token,JSON.stringify(result)])).rows[0].ok,true);
assert.equal((await db.query('select status from runs where id=$1',[id2])).rows[0].status,'done');
assert.equal((await db.query('select count(*)::int as n from run_results where run_id=$1',[id2])).rows[0].n,1);
assert.equal((await db.query('select research_finish($1,$2,$3::jsonb,null) as ok',[id2,retry.lease_token,JSON.stringify(result)])).rows[0].ok,false);
await role('authenticated',member);
const id3=await enqueue({...request,request_key:'10000000-0000-4000-8000-000000000003'});
await role('service_role');
for (let attempt=1;attempt<=3;attempt++) {
  const running=await claim(); assert.equal(running.id,id3); assert.equal(running.attempts,attempt);
  await db.exec("update research_worker_slot set expires_at=clock_timestamp()-interval '1 second'");
}
assert.equal(await claim(),null);
assert.equal((await db.query('select status from runs where id=$1',[id3])).rows[0].status,'failed');
await role('anon');
const registeredKey='20000000-0000-4000-8000-000000000001';
const enqueueRegistered = async (hyp,key=registeredKey) => (await db.query('select research_enqueue_registered($1,$2) id',[hyp,key])).rows[0].id;
await assert.rejects(enqueueRegistered('H-0009'),/permission denied/);
await role('authenticated',outsider);
await assert.rejects(enqueueRegistered('H-0009'),/Medlemsåtkomst/);
await role('service_role');
await db.query("insert into hypotheses(id,registered_at,registry_commit,statement,decision) values ('H-0009','2026-11-01','8730a1a','Frozen protocol','REJECT')");
await role('authenticated',member);
await assert.rejects(enqueueRegistered('H-9999'),/hypotes/);
const rid=await enqueueRegistered('H-0009');
assert.equal(await enqueueRegistered('H-0009'),rid);
await assert.rejects(enqueueRegistered('H-0010'),/request_key/);
await role('service_role');
const registeredJob=await claim();assert.equal(registeredJob.id,rid);assert.equal(registeredJob.kind,'registered');
assert.deepEqual(registeredJob.params,{reproduction:'frozen_windows_v1'});
assert.equal(registeredJob.period_end.slice(0,10),'2025-01-01');
await assert.rejects(db.query('select research_finish($1,$2,$3::jsonb,null)',[rid,registeredJob.lease_token,JSON.stringify(result)]),/Ogiltigt resultat/);
const registeredResult={...result,mode:'registered',hypothesis_id:'H-0009',reproduction_match:true};
assert.equal((await db.query('select research_finish($1,$2,$3::jsonb,null) ok',[rid,registeredJob.lease_token,JSON.stringify(registeredResult)])).rows[0].ok,true);
assert.equal((await db.query('select decision from hypotheses where id=$1',['H-0009'])).rows[0].decision,'REJECT');
console.log('PASS: registered enqueue permissions, fixed protocol, idempotency, shared lease, result kind fencing, registry decision unchanged.');
console.log('PASS: migrations, grants, member/nonmember/anon RLS, idempotent enqueue, single slot, cancellation, lease recovery, stale fencing, atomic result.');
console.log('PGlite uses one connection: real multi-connection contention still requires a PostgreSQL/Supabase test.');
await db.close();
