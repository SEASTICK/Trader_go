// Isolated PostgreSQL restore drill. Never connects to Supabase or a live database.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite');
const backup=JSON.parse(gunzipSync(readFileSync(process.argv[2])));
assert.equal(backup.contract_version,1);
const db=new PGlite();
await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
 create schema auth; create table auth.users(id uuid primary key);
 create function auth.uid() returns uuid language sql stable as
 $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
 grant usage on schema public,auth to anon,authenticated,service_role;
 grant execute on function auth.uid() to public;`);
for(const file of ['0001_research.sql','0002_research_members.sql','0003_research_queue.sql'])
 await db.exec(readFileSync(new URL('../supabase/migrations/'+file,import.meta.url),'utf8'));
const keys={candles:['provider','market','symbol','interval','open_time'],funding_rates:['symbol','funding_time'],
 strategies:['name','version'],hypotheses:['id'],research_members:['user_id'],runs:['id'],run_results:['run_id'],run_trades:['run_id','n']};
assert.deepEqual(Object.keys(backup.tables).sort(),Object.keys(keys).sort());
// Only UUID placeholders for FK checks. This does not restore real Auth accounts.
const userIds=new Set([...backup.tables.research_members.map(r=>r.user_id),...backup.tables.runs.map(r=>r.created_by)].filter(Boolean));
await db.exec('begin');
for(const id of userIds) await db.query('insert into auth.users(id) values ($1)',[id]);
for(const table of Object.keys(keys)){
 const rows=backup.tables[table];
 for(let i=0;i<rows.length;i+=250)
   await db.query(`insert into ${table} select * from jsonb_populate_recordset(null::${table},$1::jsonb)`,[JSON.stringify(rows.slice(i,i+250))]);
}
await db.exec('commit');
const counts={};
for(const table of Object.keys(keys)){
 const rows=backup.tables[table];
 const count=(await db.query(`select count(*)::int n from ${table}`)).rows[0].n;
 assert.equal(count,rows.length);
 for(let i=0;i<rows.length;i+=500){
   const page=rows.slice(i,i+500);
   const r=(await db.query(`select count(*)::int n,bool_and(to_jsonb(a)=to_jsonb(b)) same from ${table} a join jsonb_populate_recordset(null::${table},$1::jsonb) b using (${keys[table].join(',')})`,[JSON.stringify(page)])).rows[0];
   assert.equal(r.n,page.length);assert.equal(r.same,true);
 }
 counts[table]=count;
}
await db.exec('set role anon');
await assert.rejects(db.query('select * from run_results'),/permission denied/);
await db.exec('reset role');
if(userIds.size){
 const member=backup.tables.research_members[0]?.user_id;
 if(member){
   await db.query("select set_config('request.jwt.claim.sub',$1,false)",[member]);
   await db.exec('set role authenticated');
   await assert.rejects(db.query("insert into candles(provider) values ('test')"),/permission denied/);
   await db.query('select * from run_results limit 1');
 }
}
await db.close();
console.log(JSON.stringify({isolated_restore:'PASS',all_typed_values_equal:true,rls_after_restore:'PASS',counts,
 auth_accounts_restored:false,provider_disaster_recovery_tested:false,backup_sha256:backup.tables_sha256},null,2));
