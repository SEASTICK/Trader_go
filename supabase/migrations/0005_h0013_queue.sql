-- H-0013 (Fas 2) i samma kö och samma enda worker. Se docs/fas2-ko-tolkningar.md (K1–K12).
-- Ingen ny tabell, ingen ändring av utgivna tabeller, inget beslut skrivs till hypotheses.
-- Appliceras först efter granskning och uttryckligt ja.
begin;

create function public.research_enqueue_h0013(p_request_key uuid) returns uuid
language plpgsql security definer set search_path = '' as $$
declare uid uuid := auth.uid(); r public.runs;
begin
  if uid is null or not exists(select 1 from public.research_members where user_id = uid) then
    raise exception 'Medlemsåtkomst krävs' using errcode = '42501';
  end if;
  perform pg_advisory_xact_lock(78219341);
  -- Samma lås som återgången tar. Har en återgång tagit bort kön medan detta anrop väntade, avbryts det här,
  -- innan något sparas (en ny ögonblicksbild efter låset ser den borttagna funktionen).
  if to_regprocedure('public.research_enqueue_h0013(uuid)') is null then
    raise exception 'H-0013-kön är stängd';
  end if;
  if p_request_key is null then raise exception 'request_key krävs'; end if;
  select * into r from public.runs where request_key = p_request_key;
  if found then
    if r.created_by <> uid or r.kind <> 'registered' or r.hypothesis_id is distinct from 'H-0013' then
      raise exception 'Ogiltig request_key';
    end if;
    return r.id;
  end if;
  if not exists(select 1 from public.hypotheses where id = 'H-0013' and registry_commit <> '') then
    raise exception 'H-0013 saknas i det synkade registret';
  end if;
  if exists(select 1 from public.runs where hypothesis_id = 'H-0013' and status in ('queued', 'running')) then
    raise exception 'En H-0013-körning är redan köad eller pågår';
  end if;
  if exists(select 1 from public.runs where hypothesis_id = 'H-0013' and status = 'done') then
    raise exception 'H-0013 har redan ett resultat; en ny körning kräver ett nytt beslut';
  end if;
  if (select count(*) from public.runs where created_by = uid and status in ('queued', 'running')) >= 5
     or (select count(*) from public.runs where status in ('queued', 'running')) >= 100 then
    raise exception 'Kön är full';
  end if;
  insert into public.runs(kind, hypothesis_id, strategy, version, params, market, symbol, interval,
                          period_start, period_end, capital, costs, created_by, request_key)
  values ('registered', 'H-0013', 'h0013_adaptive_playbook', 'h0013-evaluation/1.0.0',
          '{"protocol":"research/fas2-protokoll.md","n_permutations":200,"playbooks":81}',
          'um', 'BTCUSDT', '4h', '2020-01-01T00:00:00Z', '2025-01-01T00:00:00Z', 100000,
          '{"fee_bps":10,"spread_bps":2,"slippage_bps":5}', uid, p_request_key)
  returning * into r;
  return r.id;
end $$;

-- H-0013:s resultatkontrakt (K6): exakt fem namngivna booleska kriterier, ett beslut som följer av dem,
-- booleskt holdout_loaded = false och det frysta datasetet. Allt annat avvisas innan något sparas.
create function public.research_h0013_result_ok(p jsonb) returns boolean
language plpgsql immutable set search_path = '' as $$
declare names text[]; all_true boolean;
begin
  if p->>'hypothesis_id' is distinct from 'H-0013'
     or p->>'evaluation_version' is distinct from 'h0013-evaluation/1.0.0'
     or p->>'status' is distinct from 'completed'
     or p->'holdout_loaded' is distinct from 'false'::jsonb
     or p->>'dataset_sha256' is distinct from '6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c'
     or jsonb_typeof(p->'criteria') is distinct from 'object'
     or jsonb_typeof(p->'decision') is distinct from 'string' then
    return false;
  end if;
  select array_agg(k order by k) into names from jsonb_object_keys(p->'criteria') as k;
  if names is distinct from array['sharpe_above_best_candidate', 'sharpe_above_buy_and_hold',
                                  'sharpe_above_equal_weight_mix', 'stressed_costs_positive',
                                  't_at_least_required'] then
    return false;
  end if;
  if exists(select 1 from jsonb_each(p->'criteria') as e(k, v) where jsonb_typeof(v) <> 'boolean') then
    return false;
  end if;
  select bool_and(v = 'true'::jsonb) into all_true from jsonb_each(p->'criteria') as e(k, v);
  return p->>'decision' = case when all_true then 'MORE_RESEARCH' else 'REJECT' end;
end $$;

-- Samma funktion som 0004, plus ett eget, strikt resultatkontrakt för H-0013 (K6).
create or replace function public.research_finish(p_id uuid, p_token uuid, p_result jsonb default null,
                                                  p_error text default null)
returns boolean language plpgsql security invoker set search_path = '' as $$
declare slot public.research_worker_slot; r public.runs;
begin
  select * into slot from public.research_worker_slot where singleton for update;
  if slot.run_id is distinct from p_id or slot.token is distinct from p_token
     or slot.expires_at <= clock_timestamp() then return false; end if;
  select * into r from public.runs where id = p_id for update;
  if r.status = 'running' then
    if p_error is not null then
      update public.runs set status = 'failed', error = left(p_error, 2000), finished_at = clock_timestamp()
        where id = p_id;
    else
      if jsonb_typeof(p_result->'stats') is distinct from 'object'
         or jsonb_typeof(p_result->'curves') is distinct from 'object'
         or p_result->>'mode' is distinct from r.kind
         or (r.kind = 'registered' and r.hypothesis_id <> 'H-0013'
             and (p_result->>'hypothesis_id' is distinct from r.hypothesis_id
                  or p_result->>'reproduction_match' is distinct from 'true'))
         or (r.hypothesis_id = 'H-0013' and not public.research_h0013_result_ok(p_result))
      then raise exception 'Ogiltigt resultat'; end if;
      insert into public.run_results(run_id, stats, curves, payload)
        values (p_id, p_result->'stats', p_result->'curves', p_result);
      insert into public.run_trades(run_id, n, side, entry_time, entry_price, exit_time, exit_price, net_return, exit_reason)
        select p_id, (ord - 1)::integer, x->>'side', (x->>'entry_time')::timestamptz,
          (x->>'entry_price')::double precision, (x->>'exit_time')::timestamptz,
          (x->>'exit_price')::double precision, (x->>'net_return')::double precision, x->>'exit_reason'
        from jsonb_array_elements(coalesce(p_result->'trades', '[]'::jsonb)) with ordinality as a(x, ord);
      update public.runs set status = 'done', progress = 1, finished_at = clock_timestamp() where id = p_id;
    end if;
  end if;
  update public.research_worker_slot set run_id = null, token = null, worker = null, expires_at = null where singleton;
  return true;
end $$;

revoke all on function public.research_h0013_result_ok(jsonb) from public, anon, authenticated;
grant execute on function public.research_h0013_result_ok(jsonb) to service_role;
revoke all on function public.research_enqueue_h0013(uuid) from public, anon, authenticated;
grant execute on function public.research_enqueue_h0013(uuid) to authenticated;
revoke all on function public.research_finish(uuid, uuid, jsonb, text) from public, anon, authenticated;
grant execute on function public.research_finish(uuid, uuid, jsonb, text) to service_role;
notify pgrst, 'reload schema';
commit;
