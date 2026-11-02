// Samtidighet i H-0013-kön (0001–0005) med flera riktiga PostgreSQL-anslutningar, mot en engångsdatabas.
// Kör aldrig mot Supabase: skriptet vägrar allt annat än localhost och skapar en egen databas som tas bort efteråt.
//
//   npm install --prefix /tmp/tradergo-pg-test pg@8.13.1 embedded-postgres@17.5.0-beta.15
//   scripts/run-h0013-concurrency-local.sh        # startar en tillfällig PostgreSQL och kör detta skript
//
// Eller med en egen lokal PostgreSQL: PG_ADMIN_URL=postgres://user@127.0.0.1:5432/postgres node scripts/test-h0013-concurrency.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const pg = (await import(process.env.PG_MODULE ?? 'pg')).default;

const admin = new URL(process.env.PG_ADMIN_URL ?? 'postgres://postgres@127.0.0.1:54329/postgres');
if (!['127.0.0.1', 'localhost', '::1'].includes(admin.hostname)) {
  throw new Error(`Vägrar köra mot ${admin.hostname}: samtidighetstestet är bara för en lokal engångsdatabas`);
}
const dbName = `h0013_concurrency_${process.pid}`;
const adminClient = new pg.Client({ connectionString: admin.toString() });
await adminClient.connect();
await adminClient.query(`create database ${dbName}`);
for (const r of ['anon', 'authenticated', 'service_role']) {
  await adminClient.query(`do $$ begin create role ${r} ${r === 'service_role' ? 'bypassrls' : ''}; exception when duplicate_object then null; end $$`);
}
const url = new URL(admin); url.pathname = '/' + dbName;
const member = '00000000-0000-4000-8000-000000000001';
const DATASET = '6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c';
const crit = { t_at_least_required: false, stressed_costs_positive: false, sharpe_above_buy_and_hold: true,
               sharpe_above_best_candidate: false, sharpe_above_equal_weight_mix: false };
const good = { mode: 'registered', hypothesis_id: 'H-0013', evaluation_version: 'h0013-evaluation/1.0.0', status: 'completed',
               decision: 'REJECT', criteria: crit, dataset_sha256: DATASET, holdout_loaded: false,
               stats: { sharpe: 0.1 }, curves: { t: [], equity: [] }, trades: [] };
const clients = [];

async function connect(role, uid = '') {
  const c = new pg.Client({ connectionString: url.toString() });
  await c.connect();
  await c.query("select set_config('request.jwt.claim.sub',$1,false)", [uid]);
  if (role) await c.query('set role ' + role);
  clients.push(c);
  return c;
}

try {
  const setup = await connect(null);
  await setup.query(`create schema auth; create table auth.users(id uuid primary key);
    create function auth.uid() returns uuid language sql stable as
    $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
    grant usage on schema public,auth to anon,authenticated,service_role;
    grant execute on function auth.uid() to public;
    insert into auth.users values ('${member}');`);
  for (const name of ['0001_research.sql', '0002_research_members.sql', '0003_research_queue.sql',
                      '0004_registered_reproduction.sql', '0005_h0013_queue.sql']) {
    await setup.query(readFileSync(new URL('../supabase/migrations/' + name, import.meta.url), 'utf8'));
  }
  await setup.query('insert into research_members(user_id) values ($1)', [member]);
  await setup.query("insert into hypotheses(id,registered_at,registry_commit,statement) values ('H-0013','2026-11-02','d88eaac','Fas 2')");
  const reset = () => setup.query(`delete from run_trades; delete from run_results; delete from runs;
    update research_worker_slot set run_id=null,token=null,worker=null,expires_at=null`);

  const N = 8;
  const members = await Promise.all(Array.from({ length: N }, () => connect('authenticated', member)));
  const workers = await Promise.all(Array.from({ length: N }, () => connect('service_role')));
  const key = n => `40000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
  const settle = ps => Promise.allSettled(ps);
  const count = async q => (await setup.query(q)).rows[0].n;

  // 1. Samtidiga köningar med olika nycklar: exakt en lyckas (rådgivande lås + en aktiv körning)
  let r = await settle(members.map((c, i) => c.query('select research_enqueue_h0013($1) id', [key(i)])));
  assert.equal(r.filter(x => x.status === 'fulfilled').length, 1, 'one enqueue wins');
  assert.ok(r.filter(x => x.status === 'rejected').every(x => /redan köad eller pågår/.test(x.reason.message)));
  assert.equal(await count("select count(*)::int n from runs where hypothesis_id='H-0013'"), 1);
  await reset();

  // 2. Samma nyckel från många anslutningar: samma id, en rad
  r = await settle(members.map(c => c.query('select research_enqueue_h0013($1) id', [key(100)])));
  const ids = new Set(r.map(x => x.status === 'fulfilled' ? x.value.rows[0].id : x.reason.message));
  assert.equal(ids.size, 1, 'same request_key gives the same run'); assert.equal(await count('select count(*)::int n from runs'), 1);

  // 3. Åtta workers reserverar samtidigt: exakt en får jobbet
  r = await settle(workers.map(c => c.query("select research_claim('w') job")));
  const won = r.filter(x => x.status === 'fulfilled' && x.value.rows[0].job);
  assert.equal(won.length, 1, 'exactly one worker claims');
  assert.ok(r.every(x => x.status === 'fulfilled'), 'losers get null, not an error');
  const job = won[0].value.rows[0].job;

  // 4. Samtidiga heartbeat och reservationer under giltig lease: ingen ny reservation
  r = await settle([...workers.slice(0, 4).map(c => c.query("select research_claim('w') job")),
                    ...workers.slice(4).map(c => c.query('select research_heartbeat($1,$2,0.5) s', [job.id, job.lease_token]))]);
  assert.ok(r.slice(0, 4).every(x => x.value.rows[0].job === null));
  assert.ok(r.slice(4).every(x => x.value.rows[0].s === 'running'));

  // 5. Samma resultat publiceras samtidigt från många anslutningar: exakt en lyckas, ett resultat
  r = await settle(workers.map(c => c.query('select research_finish($1,$2,$3::jsonb,null) ok', [job.id, job.lease_token, JSON.stringify(good)])));
  assert.equal(r.filter(x => x.status === 'fulfilled' && x.value.rows[0].ok === true).length, 1, 'one publish wins');
  assert.equal(await count('select count(*)::int n from run_results'), 1);
  assert.equal((await setup.query('select status from runs where id=$1', [job.id])).rows[0].status, 'done');

  // 6. Utgången lease: gammal token publicerar samtidigt som en ny worker reserverar
  await reset();
  const fresh = (await members[0].query('select research_enqueue_h0013($1) id', [key(200)])).rows[0].id;
  const first = (await workers[0].query("select research_claim('w1') job")).rows[0].job;
  assert.equal(first.id, fresh);
  await setup.query("update research_worker_slot set expires_at=clock_timestamp()-interval '1 second'");
  r = await settle([workers[1].query("select research_claim('w2') job"),
                    ...workers.slice(2).map(c => c.query('select research_finish($1,$2,$3::jsonb,null) ok', [fresh, first.lease_token, JSON.stringify(good)]))]);
  assert.ok(r.slice(1).every(x => x.status === 'fulfilled' && x.value.rows[0].ok === false), 'stale token never publishes');
  const retried = r[0].value.rows[0].job;
  assert.equal(retried.id, fresh); assert.equal(retried.attempts, 2); assert.notEqual(retried.lease_token, first.lease_token);
  assert.equal(await count('select count(*)::int n from run_results'), 0);

  // 7. Avbrott och heartbeat samtidigt: ingen ny worker tar slotten innan processen stoppats
  await members[1].query('select research_cancel($1)', [fresh]);
  r = await settle([...workers.slice(0, 4).map(c => c.query("select research_claim('w') job")),
                    workers[4].query('select research_heartbeat($1,$2,0.5) s', [fresh, retried.lease_token])]);
  assert.ok(r.slice(0, 4).every(x => x.value.rows[0].job === null));
  assert.equal(r[4].value.rows[0].s, 'cancelled');

  console.log(`PASS: ${N} connections: one enqueue, idempotent key, one claim, no claim under a valid lease, one publish,`);
  console.log('PASS: stale token never publishes while a new worker reclaims (attempt 2), cancelled run keeps the slot.');
} finally {
  for (const c of clients) await c.end().catch(() => {});
  await adminClient.query(`drop database if exists ${dbName} with (force)`).catch(() => {});
  await adminClient.end();
}
