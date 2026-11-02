// H-0013-kökontraktet (0005) i isolerad PostgreSQL (PGlite) med Supabase-liknande roller. Inget moln.
// npm install --prefix /tmp/tradergo-pg-test @electric-sql/pglite
// PGLITE_MODULE=/tmp/tradergo-pg-test/node_modules/@electric-sql/pglite/dist/index.js node scripts/test-h0013-queue.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite');
const db = new PGlite();
const member = '00000000-0000-4000-8000-000000000001';
const outsider = '00000000-0000-4000-8000-000000000002';
const DATASET = '6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c';
await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
  create schema auth; create table auth.users(id uuid primary key);
  create function auth.uid() returns uuid language sql stable as
  $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
  grant usage on schema public,auth to anon,authenticated,service_role;
  grant execute on function auth.uid() to public;
  insert into auth.users values ('${member}'),('${outsider}');`);
for (const name of ['0001_research.sql', '0002_research_members.sql', '0003_research_queue.sql',
                    '0004_registered_reproduction.sql', '0005_h0013_queue.sql']) {
  await db.exec(readFileSync(new URL('../supabase/migrations/' + name, import.meta.url), 'utf8'));
}
await db.query('insert into research_members(user_id) values ($1)', [member]);
async function role(name, uid = '') {
  await db.exec('reset role');
  await db.query("select set_config('request.jwt.claim.sub',$1,false)", [uid]);
  await db.exec('set role ' + name);
}
const key = n => `30000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
const enqueue = async (k = key(1)) => (await db.query('select research_enqueue_h0013($1) as id', [k])).rows[0].id;
const claim = async () => (await db.query("select research_claim('test-worker') as job")).rows[0].job;
const finish = async (id, token, result, error = null) =>
  (await db.query('select research_finish($1,$2,$3::jsonb,$4) as ok', [id, token, result && JSON.stringify(result), error])).rows[0].ok;
const expire = () => db.exec("update research_worker_slot set expires_at=clock_timestamp()-interval '1 second'");
const status = async id => (await db.query('select status,attempts,error from runs where id=$1', [id])).rows[0];
const crit = { t_at_least_required: false, stressed_costs_positive: false, sharpe_above_buy_and_hold: true,
               sharpe_above_best_candidate: false, sharpe_above_equal_weight_mix: false };
const good = { mode: 'registered', hypothesis_id: 'H-0013', evaluation_version: 'h0013-evaluation/1.0.0',
               status: 'completed', decision: 'REJECT', criteria: crit, dataset_sha256: DATASET, holdout_loaded: false,
               stats: { sharpe: 0.1 }, curves: { t: [], equity: [] },
               trades: [{ side: 'Long', entry_time: '2022-01-02T04:00:00Z', entry_price: 1, exit_time: '2022-01-03T00:00:00Z',
                          exit_price: 1.1, net_return: 0.1, exit_reason: 'signal' }] };

// K2: autentisering och RLS
await role('anon');
await assert.rejects(enqueue(), /permission denied/);
await role('authenticated', outsider);
await assert.rejects(enqueue(), /Medlemsåtkomst/);
await role('authenticated', member);
await assert.rejects(db.query("insert into runs(kind,hypothesis_id,strategy,version,market,symbol,interval,period_start,period_end) values ('registered','H-0013','x','x','um','BTCUSDT','4h','2020-01-01','2025-01-01')"), /permission denied/);
await assert.rejects(db.query("select research_finish(gen_random_uuid(),gen_random_uuid(),'{}'::jsonb,null)"), /permission denied/);
await assert.rejects(db.query("select research_claim('member')"), /permission denied/);
// K4: H-0013 måste finnas i det synkade registret
await assert.rejects(enqueue(), /H-0013 saknas/);
await role('service_role');
await db.query("insert into hypotheses(id,registered_at,registry_commit,statement) values ('H-0013','2026-11-02','d88eaac','Fas 2')");
await role('authenticated', member);
const id = await enqueue(key(1));
assert.equal(await enqueue(key(1)), id, 'same request_key is idempotent');
await assert.rejects(enqueue(key(2)), /redan köad eller pågår/);
// K3: allt är fast
const row = (await db.query('select * from runs where id=$1', [id])).rows[0];
assert.equal(row.kind, 'registered'); assert.equal(row.hypothesis_id, 'H-0013');
assert.equal(row.strategy, 'h0013_adaptive_playbook'); assert.equal(row.version, 'h0013-evaluation/1.0.0');
assert.deepEqual(row.params, { protocol: 'research/fas2-protokoll.md', n_permutations: 200, playbooks: 81 });
assert.equal(row.period_end.toISOString().slice(0, 10), '2025-01-01');
await role('authenticated', outsider);
assert.equal((await db.query('select * from runs')).rows.length, 0, 'non-members see no runs');
await assert.rejects(db.query('select research_enqueue_h0013($1)', [key(1)]), /Medlemsåtkomst/);

// K5, K8, K9: samma slot, lease, återförsök och fencing
await role('service_role');
const first = await claim(); assert.equal(first.id, id); assert.equal(first.attempts, 1);
assert.equal(await claim(), null, 'one global slot');
await expire();                                            // workern dog: leasen löper ut
const second = await claim(); assert.equal(second.id, id); assert.equal(second.attempts, 2);
assert.notEqual(second.lease_token, first.lease_token);
assert.equal(await finish(id, first.lease_token, good), false, 'stale token cannot publish');
assert.equal((await db.query('select count(*)::int n from run_results')).rows[0].n, 0);
const slotBefore = (await db.query('select * from research_worker_slot')).rows[0];
const allTrue = Object.fromEntries(Object.keys(crit).map(k => [k, true]));
const { t_at_least_required, ...four } = crit;
const invalid = [
  ['hypothesis_id', { ...good, hypothesis_id: 'H-0012' }], ['evaluation_version', { ...good, evaluation_version: 'h0013-evaluation/2.0.0' }],
  ['status', { ...good, status: 'aborted' }], ['decision READY_FOR_PAPER', { ...good, decision: 'READY_FOR_PAPER' }],
  ['decision null', { ...good, decision: null }], ['decision missing', (({ decision, ...x }) => x)(good)],
  ['dataset', { ...good, dataset_sha256: 'f'.repeat(64) }], ['mode', { ...good, mode: 'exploration' }], ['stats', { ...good, stats: 'x' }],
  // Granskningens prov: godtyckliga kriterier, motsägande beslut och holdout som sträng
  ['arbitrary criteria', { ...good, decision: 'MORE_RESEARCH', criteria: { a: 'x', b: null, c: 123, d: {}, e: [] } }],
  ['MORE_RESEARCH with false criteria', { ...good, decision: 'MORE_RESEARCH' }],
  ['REJECT with all true', { ...good, decision: 'REJECT', criteria: allTrue }],
  ['holdout string', { ...good, holdout_loaded: 'false' }], ['holdout true', { ...good, holdout_loaded: true }],
  ['holdout null', { ...good, holdout_loaded: null }], ['holdout missing', (({ holdout_loaded, ...x }) => x)(good)],
  ['missing criterion', { ...good, criteria: four }], ['extra criterion', { ...good, criteria: { ...crit, stability: true } }],
  ['renamed criterion', { ...good, criteria: { ...four, t_required: false } }], ['criteria array', { ...good, criteria: [false, false, true, false, false] }],
];
for (const v of [null, 'false', 0, 1, {}, [], 'true']) invalid.push([`criterion value ${JSON.stringify(v)}`, { ...good, criteria: { ...crit, t_at_least_required: v } }]);
for (const [name, result] of invalid) {
  await assert.rejects(finish(id, second.lease_token, result), /Ogiltigt resultat/, name);
}
const slotAfter = (await db.query('select * from research_worker_slot')).rows[0];
assert.deepEqual(slotAfter, slotBefore, 'a rejected result leaves the slot and lease unchanged');
assert.equal((await status(id)).status, 'running');
assert.equal((await db.query('select count(*)::int n from run_results')).rows[0].n, 0);
const { reproduction_match, ...noRepro } = { ...good };
assert.equal(await finish(id, second.lease_token, noRepro), true);
assert.equal((await status(id)).status, 'done');
assert.equal((await db.query('select count(*)::int n from run_results where run_id=$1', [id])).rows[0].n, 1);
assert.equal((await db.query('select count(*)::int n from run_trades where run_id=$1', [id])).rows[0].n, 1);
assert.equal(await finish(id, second.lease_token, good), false, 'a second publish is refused');
assert.equal((await db.query('select count(*)::int n from run_results where run_id=$1', [id])).rows[0].n, 1);
assert.equal((await db.query("select decision from hypotheses where id='H-0013'")).rows[0].decision, null,
             'the registry decision is not written by the queue');
await role('authenticated', member);
await assert.rejects(enqueue(key(3)), /redan ett resultat/);

// Avbrott, tre försök och fel med ny databas
await db.exec('reset role'); await db.exec("delete from run_trades; delete from run_results; delete from runs where hypothesis_id='H-0013'");
await role('authenticated', member);
const cancelId = await enqueue(key(4));
await role('service_role');
const running = await claim(); assert.equal(running.id, cancelId);
await role('authenticated', member);
assert.equal((await db.query('select research_cancel($1) ok', [cancelId])).rows[0].ok, true);
await role('service_role');
assert.equal((await db.query('select research_heartbeat($1,$2,0.4) s', [cancelId, running.lease_token])).rows[0].s, 'cancelled');
assert.equal(await claim(), null, 'a cancelled process keeps the slot until it stops');
assert.equal(await finish(cancelId, running.lease_token, null, 'Avbruten'), true);
assert.equal((await status(cancelId)).status, 'cancelled');
await role('authenticated', member);
const retryId = await enqueue(key(5));
await role('service_role');
for (let attempt = 1; attempt <= 3; attempt++) {
  const job = await claim(); assert.equal(job.id, retryId); assert.equal(job.attempts, attempt);
  await expire();
}
assert.equal(await claim(), null);
assert.deepEqual([(await status(retryId)).status, (await status(retryId)).attempts], ['failed', 3]);
await role('authenticated', member);
const timeoutId = await enqueue(key(6));
await role('service_role');
const timed = await claim();
assert.equal(await finish(timeoutId, timed.lease_token, null, 'Worker stoppad eller tidsgräns nådd'), true);
assert.equal((await status(timeoutId)).status, 'failed');

// MORE_RESEARCH accepteras bara när alla fem är sanna
await db.exec('reset role'); await db.exec("delete from run_trades; delete from run_results; delete from runs where hypothesis_id='H-0013'");
await role('authenticated', member);
const moreId = await enqueue(key(9));
await role('service_role');
const more = await claim(); assert.equal(more.id, moreId);
assert.equal(await finish(moreId, more.lease_token, { ...good, decision: 'MORE_RESEARCH', criteria: allTrue }), true);
assert.equal((await status(moreId)).status, 'done');
for (const r of ['anon', 'authenticated']) {
  await role(r, r === 'authenticated' ? member : '');
  await assert.rejects(db.query("select research_h0013_result_ok('{}'::jsonb)"), /permission denied/);
}

// Befintliga flöden oförändrade efter 0005
await role('service_role');
await db.query("insert into hypotheses(id,registered_at,registry_commit,statement,decision) values ('H-0009','2026-11-01','8730a1a','Fas 1','REJECT')");
await role('authenticated', member);
const rid = (await db.query('select research_enqueue_registered($1,$2) id', ['H-0009', key(7)])).rows[0].id;
await role('service_role');
const reg = await claim(); assert.equal(reg.id, rid);
const base = { mode: 'registered', stats: { a: 1 }, curves: { t: [] }, trades: [] };
await assert.rejects(finish(rid, reg.lease_token, { ...base, hypothesis_id: 'H-0009' }), /Ogiltigt resultat/);
assert.equal(await finish(rid, reg.lease_token, { ...base, hypothesis_id: 'H-0009', reproduction_match: true }), true);
await role('authenticated', member);
const ex = (await db.query('select research_enqueue($1::jsonb) id', [JSON.stringify({ request_key: key(8), strategy: 'ema_adx_trend',
  market: 'um', interval: '4h', period_start: '2022-01-01T00:00:00Z', period_end: '2022-03-01T00:00:00Z', params: {} })])).rows[0].id;
await role('service_role');
const exJob = await claim(); assert.equal(exJob.id, ex);
assert.equal(await finish(ex, exJob.lease_token, { mode: 'exploration', stats: {}, curves: {}, trades: [] }), true);
await role('anon');
await assert.rejects(db.query("select research_finish(gen_random_uuid(),gen_random_uuid(),'{}'::jsonb,null)"), /permission denied/);

console.log('PASS: H-0013 enqueue auth/RLS, fixed contract, registry precondition, one active run, no second result.');
console.log('PASS: shared slot, lease expiry retry (3 attempts), stale fencing, duplicate publish refused.');
console.log(`PASS: strict result contract rejects ${invalid.length} invalid results (names, booleans, decision consistency, boolean holdout) and leaves the lease unchanged.`);
console.log('PASS: cancellation, timeout failure, registry decision untouched, Fas 1 registered and exploration flows unchanged.');
console.log('PGlite uses one connection: real multi-connection contention still requires a PostgreSQL/Supabase test.');
await db.close();
