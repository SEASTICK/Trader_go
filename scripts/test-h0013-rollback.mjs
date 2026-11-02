// Återgången för 0005 i isolerad PostgreSQL (PGlite). Inget moln.
// PGLITE_MODULE=/tmp/tradergo-pg-test/node_modules/@electric-sql/pglite/dist/index.js node scripts/test-h0013-rollback.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite');
const sql = path => readFileSync(new URL('../supabase/' + path, import.meta.url), 'utf8');
const base = `create role anon; create role authenticated; create role service_role bypassrls;
  create schema auth; create table auth.users(id uuid primary key);
  create function auth.uid() returns uuid language sql stable as
  $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
  grant usage on schema public,auth to anon,authenticated,service_role;
  grant execute on function auth.uid() to public;`;
async function database(migrations) {
  const db = new PGlite();
  await db.exec(base);
  for (const m of migrations) await db.exec(sql('migrations/' + m));
  return db;
}
const upTo4 = ['0001_research.sql', '0002_research_members.sql', '0003_research_queue.sql', '0004_registered_reproduction.sql'];
const reference = await database(upTo4);
const db = await database([...upTo4, '0005_h0013_queue.sql']);
const fn = async (d, name) => (await d.query("select prosrc, proconfig, prosecdef from pg_proc where proname=$1", [name])).rows;
const grants = async (d, name) => (await d.query(`select r.rolname, has_function_privilege(r.rolname, p.oid, 'execute') ok
  from pg_proc p, pg_roles r where p.proname=$1 and r.rolname in ('anon','authenticated','service_role') order by 1`, [name])).rows;

// Vägrar när H-0013-körningar finns: inget resultat eller försök får försvinna i tysthet.
await db.query("insert into hypotheses(id,registered_at,registry_commit,statement) values ('H-0013','2026-11-02','d88eaac','Fas 2')");
await db.query("insert into runs(kind,hypothesis_id,strategy,version,market,symbol,interval,period_start,period_end) values ('registered','H-0013','h0013_adaptive_playbook','h0013-evaluation/1.0.0','um','BTCUSDT','4h','2020-01-01','2025-01-01')");
await assert.rejects(db.exec(sql('rollback/0005_h0013_queue_down.sql')), /H-0013-körningar finns/);
await db.exec('rollback'); // avsluta den avbrutna transaktionen
assert.equal((await fn(db, 'research_enqueue_h0013')).length, 1, 'a refused rollback changes nothing');
assert.equal((await db.query('select count(*)::int n from runs')).rows[0].n, 1);

// Utan H-0013-körningar: tillbaka till exakt 0004.
await db.query("delete from runs where hypothesis_id='H-0013'");
await db.exec(sql('rollback/0005_h0013_queue_down.sql'));
assert.equal((await fn(db, 'research_enqueue_h0013')).length, 0);
assert.equal((await fn(db, 'research_h0013_result_ok')).length, 0);
assert.deepEqual(await fn(db, 'research_finish'), await fn(reference, 'research_finish'), 'research_finish is exactly 0004 again');
assert.deepEqual(await grants(db, 'research_finish'), await grants(reference, 'research_finish'));
assert.equal((await db.query("select count(*)::int n from hypotheses where id='H-0013'")).rows[0].n, 1, 'no data is deleted');
// 0005 kan appliceras igen efter återgången (samma fil, inga rester).
await db.exec(sql('migrations/0005_h0013_queue.sql'));
assert.equal((await fn(db, 'research_enqueue_h0013')).length, 1);
console.log('PASS: rollback refuses while H-0013 runs exist, restores 0004 research_finish and grants exactly, keeps data, 0005 re-applies.');
await db.close(); await reference.close();
