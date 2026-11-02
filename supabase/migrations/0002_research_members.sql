-- Projektmedlemskap måste tilldelas av administratör/server, aldrig via klienten.
create table public.research_members (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.research_members enable row level security;
revoke all on public.research_members from public, anon, authenticated;
grant select on public.research_members to authenticated;
grant all on public.research_members to service_role;
create policy read_own_membership on public.research_members
  for select to authenticated using (user_id = (select auth.uid()));

-- Ändra endast kända policies från 0001. Okända befintliga policies kräver granskning.
drop policy read_candles on public.candles;
drop policy read_funding on public.funding_rates;
drop policy read_strategies on public.strategies;
drop policy read_hypotheses on public.hypotheses;
drop policy read_runs on public.runs;
drop policy read_results on public.run_results;
drop policy read_trades on public.run_trades;
drop policy queue_exploration on public.runs;
drop policy cancel_own_run on public.runs;

do $$
declare t text;
begin
  foreach t in array array['candles', 'funding_rates', 'strategies', 'hypotheses',
                           'runs', 'run_results', 'run_trades'] loop
    execute format('revoke all on public.%I from public, anon, authenticated', t);
    execute format('grant select on public.%I to authenticated', t);
    execute format('grant all on public.%I to service_role', t);
    execute format(
      'create policy member_read on public.%I for select to authenticated using
       (exists (select 1 from public.research_members where user_id = (select auth.uid())))', t);
  end loop;
end $$;

-- Köning och avbrott aktiveras med validerade RPC:er i nästa migration.
-- Ingen direkt klientskrivning innan workerns kontrakt är implementerat.
notify pgrst, 'reload schema';
