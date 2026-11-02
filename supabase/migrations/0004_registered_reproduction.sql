-- Frozen registered-window reproduction uses the same global worker slot.
-- No strategy discovery, parameter selection, new decisions or holdout access.
begin;
create function public.research_enqueue_registered(p_hypothesis text,p_request_key uuid) returns uuid
language plpgsql security definer set search_path='' as $$
declare uid uuid:=auth.uid(); r public.runs; strategy_name text;
begin
  if uid is null or not exists(select 1 from public.research_members where user_id=uid) then
    raise exception 'Medlemsåtkomst krävs' using errcode='42501'; end if;
  perform pg_advisory_xact_lock(78219341);
  if p_request_key is null then raise exception 'request_key krävs'; end if;
  select * into r from public.runs where request_key=p_request_key;
  if found then
    if r.created_by<>uid or r.kind<>'registered' or r.hypothesis_id<>p_hypothesis then
      raise exception 'Ogiltig request_key'; end if;
    return r.id;
  end if;
  strategy_name:=case p_hypothesis when 'H-0009' then 'ema_adx_trend'
    when 'H-0010' then 'donchian_breakout' when 'H-0011' then 'bb_rsi_reversion'
    when 'H-0012' then 'squeeze_breakout' end;
  if strategy_name is null or not exists(select 1 from public.hypotheses
       where id=p_hypothesis and registry_commit<>'' and decision='REJECT') then
    raise exception 'Fryst registrerad hypotes saknas'; end if;
  if (select count(*) from public.runs where created_by=uid and status in ('queued','running'))>=5
     or (select count(*) from public.runs where status in ('queued','running'))>=100 then
    raise exception 'Kön är full'; end if;
  insert into public.runs(kind,hypothesis_id,strategy,version,params,market,symbol,interval,
    period_start,period_end,capital,costs,created_by,request_key)
  values('registered',p_hypothesis,strategy_name,'1.0.0','{"reproduction":"frozen_windows_v1"}',
    'um','BTCUSDT','4h','2020-01-01T00:00:00Z','2025-01-01T00:00:00Z',100000,
    '{"fee_bps":10,"spread_bps":2,"slippage_bps":5}',uid,p_request_key) returning * into r;
  return r.id;
end $$;
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

revoke all on function public.research_enqueue_registered(text,uuid) from public,anon,authenticated;
grant execute on function public.research_enqueue_registered(text,uuid) to authenticated;
notify pgrst,'reload schema';
commit;
