begin;
alter table public.runs add column request_key uuid unique;
alter table public.runs add column attempts integer not null default 0;
alter table public.run_results add column payload jsonb;
-- 0001 gav en separat kolumnrättighet som REVOKE ALL ON TABLE inte tar bort.
revoke update (status) on public.runs from authenticated;

-- En global slot, även avbrutna jobb håller slotten tills processen stannat.
create table public.research_worker_slot (
  singleton boolean primary key default true check (singleton),
  run_id uuid references public.runs(id),
  token uuid,
  worker text,
  expires_at timestamptz
);
insert into public.research_worker_slot(singleton) values (true);
alter table public.research_worker_slot enable row level security;
revoke all on public.research_worker_slot from public, anon, authenticated;
grant all on public.research_worker_slot to service_role;

create function public.research_enqueue(p_request jsonb) returns uuid
language plpgsql security definer set search_path = '' as $$
declare r public.runs; uid uuid := auth.uid(); s timestamptz; e timestamptz;
        k uuid; strategy_name text; market_name text; frame text; p jsonb;
begin
  if uid is null or not exists(select 1 from public.research_members where user_id=uid) then
    raise exception 'Medlemsåtkomst krävs' using errcode='42501';
  end if;
  perform pg_advisory_xact_lock(78219341);
  k := (p_request->>'request_key')::uuid;
  if k is null then raise exception 'request_key krävs'; end if;
  select * into r from public.runs where request_key=k;
  if found then
    if r.created_by<>uid then raise exception 'Ogiltig request_key'; end if;
    return r.id;
  end if;
  if (select count(*) from public.runs where created_by=uid and status in ('queued','running'))>=5
     or (select count(*) from public.runs where status in ('queued','running'))>=100 then
    raise exception 'Kön är full';
  end if;
  strategy_name:=p_request->>'strategy'; market_name:=p_request->>'market'; frame:=p_request->>'interval';
  if strategy_name is null or strategy_name not in
      ('ema_adx_trend','donchian_breakout','bb_rsi_reversion','squeeze_breakout')
     or market_name is null or market_name not in ('spot','um')
     or frame is null or frame not in ('1h','4h','1d') then
    raise exception 'Ogiltig strategi, marknad eller tidsram';
  end if;
  s:=(p_request->>'period_start')::timestamptz; e:=(p_request->>'period_end')::timestamptz;
  if s is null or e is null or s<'2020-01-01T00:00:00Z' or e>'2025-01-01T00:00:00Z'
     or e<=s or e-s<interval '30 days' then
    raise exception 'Perioden ska vara minst 30 dagar inom 2020-01-01 till 2025-01-01 (exklusivt slut)';
  end if;
  if s<>date_trunc('day',s at time zone 'UTC') at time zone 'UTC'
     or e<>date_trunc('day',e at time zone 'UTC') at time zone 'UTC' then
    raise exception 'Periodgränser måste vara hela UTC-dygn';
  end if;
  p:=coalesce(p_request->'params','{}'::jsonb);
  if jsonb_typeof(p)<>'object' or octet_length(p::text)>4096 then raise exception 'Ogiltiga parametrar'; end if;
  insert into public.runs(kind,strategy,version,params,market,symbol,interval,period_start,period_end,
                          capital,costs,created_by,request_key)
  values ('exploration',strategy_name,'1.0.0',p,market_name,'BTCUSDT',frame,s,e,100000,
          '{"fee_bps":10,"spread_bps":2,"slippage_bps":5}'::jsonb,uid,k) returning * into r;
  return r.id;
end $$;

create function public.research_cancel(p_id uuid) returns boolean
language plpgsql security definer set search_path = '' as $$
begin
  if not exists(select 1 from public.research_members where user_id=auth.uid()) then
    raise exception 'Medlemsåtkomst krävs' using errcode='42501';
  end if;
  update public.runs set status='cancelled',finished_at=clock_timestamp()
    where id=p_id and created_by=auth.uid() and status in ('queued','running');
  return found;
end $$;

create function public.research_claim(p_worker text) returns jsonb
language plpgsql security invoker set search_path = '' as $$
declare slot public.research_worker_slot; r public.runs; t uuid;
begin
  select * into slot from public.research_worker_slot where singleton for update;
  if slot.run_id is not null and slot.expires_at>clock_timestamp() then return null; end if;
  if slot.run_id is not null then
    update public.runs set status=case when attempts<3 then 'queued' else 'failed' end,
      error='Worker-lease löpte ut',
      finished_at=case when attempts>=3 then clock_timestamp() else null end
      where id=slot.run_id and status='running';
  end if;
  update public.research_worker_slot set run_id=null,token=null,worker=null,expires_at=null where singleton;
  select * into r from public.runs where status='queued' order by created_at,id limit 1 for update skip locked;
  if not found then return null; end if;
  t:=gen_random_uuid();
  update public.runs set status='running',attempts=attempts+1,started_at=clock_timestamp(),
    finished_at=null,progress=0,error=null where id=r.id returning * into r;
  update public.research_worker_slot set run_id=r.id,token=t,worker=left(p_worker,200),
    expires_at=clock_timestamp()+interval '90 seconds' where singleton;
  return to_jsonb(r)||jsonb_build_object('lease_token',t);
end $$;

create function public.research_heartbeat(p_id uuid,p_token uuid,p_progress real) returns text
language plpgsql security invoker set search_path = '' as $$
declare slot public.research_worker_slot; state text;
begin
  select * into slot from public.research_worker_slot where singleton for update;
  if slot.run_id is distinct from p_id or slot.token is distinct from p_token
     or slot.expires_at<=clock_timestamp() then return 'lost'; end if;
  select status into state from public.runs where id=p_id for update;
  if state='running' then
    update public.research_worker_slot set expires_at=clock_timestamp()+interval '90 seconds' where singleton;
    update public.runs set progress=greatest(progress,least(0.99,greatest(0,p_progress))) where id=p_id;
  end if;
  return state;
end $$;

create function public.research_finish(p_id uuid,p_token uuid,p_result jsonb default null,p_error text default null)
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
         or p_result->>'mode' is distinct from 'exploration' then raise exception 'Ogiltigt resultat'; end if;
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

revoke all on function public.research_enqueue(jsonb) from public,anon,authenticated;
revoke all on function public.research_cancel(uuid) from public,anon,authenticated;
revoke all on function public.research_claim(text) from public,anon,authenticated;
revoke all on function public.research_heartbeat(uuid,uuid,real) from public,anon,authenticated;
revoke all on function public.research_finish(uuid,uuid,jsonb,text) from public,anon,authenticated;
grant execute on function public.research_enqueue(jsonb),public.research_cancel(uuid) to authenticated;
grant execute on function public.research_claim(text),public.research_heartbeat(uuid,uuid,real),
  public.research_finish(uuid,uuid,jsonb,text) to service_role;
notify pgrst,'reload schema';
commit;
