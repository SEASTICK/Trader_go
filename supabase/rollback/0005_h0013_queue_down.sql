-- Återgång för 0005_h0013_queue.sql. Körs bara vid en beslutad återgång, efter granskning, och aldrig som migration.
-- Tar bort H-0013:s köfunktioner och återställer research_finish exakt som i 0004. Rör inga tabeller och raderar
-- ingen data. Vägrar om någon H-0013-körning finns, så att inget resultat eller försök går förlorat i tysthet.
begin;

-- Samma rådgivande lås som all köning (0003–0005). En köning som redan har låset blir klar först och syns då i
-- kontrollen nedan, så återgången vägrar. En köning som startar efter detta väntar på låset och avbryts sedan av
-- research_enqueue_h0013, eftersom funktionen är borttagen när låset släpps.
select pg_advisory_xact_lock(78219341);

do $$
begin
  if exists(select 1 from public.runs where hypothesis_id = 'H-0013') then
    raise exception 'H-0013-körningar finns; återgången avbryts. Avbryt och arkivera dem först, enligt docs/fas2-driftsattning.md';
  end if;
end $$;

drop function public.research_enqueue_h0013(uuid);

create or replace function public.research_finish(p_id uuid,p_token uuid,p_result jsonb default null,p_error text default null)
returns boolean language plpgsql security invoker set search_path = '' as $$
declare slot public.research_worker_slot; r public.runs;
begin
  select * into slot from public.research_worker_slot where singleton for update;
  if slot.run_id is distinct from p_id or slot.token is distinct from p_token
     or slot.expires_at<=clock_timestamp() then return false; end if;
  select * into r from public.runs where id=p_id for update;
  if r.status='running' then
    if p_error is not null then
      update public.runs set status='failed',error=left(p_error,2000),finished_at=clock_timestamp() where id=p_id;
    else
      if jsonb_typeof(p_result->'stats') is distinct from 'object'
         or jsonb_typeof(p_result->'curves') is distinct from 'object'
         or p_result->>'mode' is distinct from r.kind
         or (r.kind='registered' and (p_result->>'hypothesis_id' is distinct from r.hypothesis_id
             or p_result->>'reproduction_match' is distinct from 'true')) then raise exception 'Ogiltigt resultat'; end if;
      insert into public.run_results(run_id,stats,curves,payload)
        values(p_id,p_result->'stats',p_result->'curves',p_result);
      insert into public.run_trades(run_id,n,side,entry_time,entry_price,exit_time,exit_price,net_return,exit_reason)
        select p_id,(ord-1)::integer,x->>'side',(x->>'entry_time')::timestamptz,
          (x->>'entry_price')::double precision,(x->>'exit_time')::timestamptz,
          (x->>'exit_price')::double precision,(x->>'net_return')::double precision,x->>'exit_reason'
        from jsonb_array_elements(coalesce(p_result->'trades','[]'::jsonb)) with ordinality as a(x,ord);
      update public.runs set status='done',progress=1,finished_at=clock_timestamp() where id=p_id;
    end if;
  end if;
  update public.research_worker_slot set run_id=null,token=null,worker=null,expires_at=null where singleton;
  return true;
end $$;

drop function public.research_h0013_result_ok(jsonb);
revoke all on function public.research_finish(uuid,uuid,jsonb,text) from public,anon,authenticated;
grant execute on function public.research_finish(uuid,uuid,jsonb,text) to service_role;
notify pgrst,'reload schema';
commit;
