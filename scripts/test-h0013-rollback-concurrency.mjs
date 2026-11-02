// Återgången för 0005 samtidigt med köning, med riktiga PostgreSQL-anslutningar (granskning av PR #74, P1).
// Bara mot en lokal engångsdatabas: scripts/run-h0013-concurrency-local.sh test-h0013-rollback-concurrency.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const pg = (await import(process.env.PG_MODULE ?? 'pg')).default;

const admin = new URL(process.env.PG_ADMIN_URL ?? 'postgres://postgres@127.0.0.1:54329/postgres');
if (!['127.0.0.1', 'localhost', '::1'].includes(admin.hostname)) {
  throw new Error(`Vägrar köra mot ${admin.hostname}: testet är bara för en lokal engångsdatabas`);
}
const sql = path => readFileSync(new URL('../supabase/' + path, import.meta.url), 'utf8');
const rollback = sql('rollback/0005_h0013_queue_down.sql');
const LOCK = 'select pg_advisory_xact_lock(78219341);';
assert.ok(rollback.includes(LOCK), 'the rollback takes the queue lock');
const member = '00000000-0000-4000-8000-000000000001';
const adminClient = new pg.Client({ connectionString: admin.toString() });
await adminClient.connect();
for (const r of ['anon', 'authenticated', 'service_role']) {
  await adminClient.query(`do $$ begin create role ${r} ${r === 'service_role' ? 'bypassrls' : ''}; exception when duplicate_object then null; end $$`);
}
const clients = [];
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function freshDatabase(tag) {
  const name = `h0013_rollback_${tag}_${process.pid}`;
  await adminClient.query(`create database ${name}`);
  const url = new URL(admin); url.pathname = '/' + name;
  const connect = async (role, uid = '') => {
    const c = new pg.Client({ connectionString: url.toString() });
    await c.connect();
    await c.query("select set_config('request.jwt.claim.sub',$1,false)", [uid]);
    if (role) await c.query('set role ' + role);
    clients.push(c);
    return c;
  };
  const setup = await connect(null);
  await setup.query(`create schema auth; create table auth.users(id uuid primary key);
    create function auth.uid() returns uuid language sql stable as
    $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
    grant usage on schema public,auth to anon,authenticated,service_role;
    grant execute on function auth.uid() to public;
    insert into auth.users values ('${member}');`);
  for (const m of ['0001_research.sql', '0002_research_members.sql', '0003_research_queue.sql',
                   '0004_registered_reproduction.sql', '0005_h0013_queue.sql']) await setup.query(sql('migrations/' + m));
  await setup.query('insert into research_members(user_id) values ($1)', [member]);
  await setup.query("insert into hypotheses(id,registered_at,registry_commit,statement) values ('H-0013','2026-11-02','d88eaac','Fas 2')");
  return { name, setup, connect };
}
const state = async setup => ({
  runs: (await setup.query("select count(*)::int n from runs where hypothesis_id='H-0013'")).rows[0].n,
  enqueue: (await setup.query("select count(*)::int n from pg_proc where proname='research_enqueue_h0013'")).rows[0].n,
  check: (await setup.query("select count(*)::int n from pg_proc where proname='research_h0013_result_ok'")).rows[0].n,
});

try {
  // Ordning 1: köningen är påbörjad men inte committad när återgången startar (granskningens prov).
  {
    const { setup, connect } = await freshDatabase('enqueue_first');
    const a = await connect('authenticated', member);
    const b = await connect(null);
    await a.query('begin');
    const id = (await a.query("select research_enqueue_h0013('50000000-0000-4000-8000-000000000001') id")).rows[0].id;
    assert.ok(id);
    let settled = false;
    const down = b.query(rollback).then(() => 'committed', e => e.message).finally(() => { settled = true; });
    await sleep(500);
    assert.equal(settled, false, 'the rollback waits for the open enqueue (same lock)');
    await a.query('commit');
    assert.match(await down, /H-0013-körningar finns/);
    await b.query('rollback').catch(() => {});
    assert.deepEqual(await state(setup), { runs: 1, enqueue: 1, check: 1 }, 'refused rollback changes nothing');
  }

  // Ordning 2: återgången har låset när ett köningsanrop startar.
  {
    const { setup, connect } = await freshDatabase('rollback_first');
    const a = await connect('authenticated', member);
    const b = await connect(null);
    // Samma fil, med en paus direkt efter låset så att köningen hinner starta och vänta på det.
    const paused = rollback.replace(LOCK, LOCK + '\nselect pg_sleep(1);');
    const down = b.query(paused).then(() => 'committed', e => e.message);
    await sleep(300);
    const enq = a.query("select research_enqueue_h0013('50000000-0000-4000-8000-000000000002') id")
      .then(r => `enqueued ${r.rows[0].id}`, e => e.message);
    assert.equal(await down, 'committed');
    assert.match(await enq, /H-0013-kön är stängd|does not exist/);
    assert.deepEqual(await state(setup), { runs: 0, enqueue: 0, check: 0 }, 'no H-0013 job survives a successful rollback');
  }

  // Ordning 3: utan låset i återgången (granskningens fel) blir det ett kvarlämnat jobb.
  {
    const { setup, connect } = await freshDatabase('without_lock');
    const a = await connect('authenticated', member);
    const b = await connect(null);
    await a.query('begin');
    await a.query("select research_enqueue_h0013('50000000-0000-4000-8000-000000000003') id");
    const down = b.query(rollback.replace(LOCK, '')).then(() => 'committed', e => e.message);
    await sleep(300);
    await a.query('commit');
    assert.equal(await down, 'committed');
    assert.deepEqual(await state(setup), { runs: 1, enqueue: 0, check: 0 }, 'shows the race the lock prevents');
  }

  console.log('PASS: enqueue first -> rollback waits and refuses, nothing changed.');
  console.log('PASS: rollback first -> waiting enqueue is refused after the lock, no H-0013 job is left.');
  console.log('PASS: control: the same race without the lock leaves 1 job and 0 functions.');
} finally {
  for (const c of clients) await c.end().catch(() => {});
  const dbs = await adminClient.query("select datname from pg_database where datname like 'h0013_rollback_%'");
  for (const { datname } of dbs.rows) await adminClient.query(`drop database if exists ${datname} with (force)`).catch(() => {});
  await adminClient.end();
}
