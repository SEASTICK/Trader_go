-- Trader_go Fas 1: forskningsdata i Supabase (PostgreSQL).
-- Bara papper och historik. Inga börsnycklar, inga order, inga personuppgifter utöver inloggningen.
-- Skrivs av workern med service-nyckeln (som bara finns på servern). Appen läser som inloggad användare.

create table if not exists candles (
  provider   text        not null,
  market     text        not null,   -- spot | um
  symbol     text        not null,
  interval   text        not null,   -- 1h | 4h | 1d
  open_time  timestamptz not null,
  open       double precision not null,
  high       double precision not null,
  low        double precision not null,
  close      double precision not null,
  volume     double precision not null,
  closed     boolean     not null default true,  -- false = pågående stapel, aldrig analysunderlag
  received_at timestamptz not null default now(),
  primary key (provider, market, symbol, interval, open_time)
);
create index if not exists candles_series_time on candles (symbol, interval, open_time desc);

create table if not exists funding_rates (
  symbol      text        not null,
  funding_time timestamptz not null,
  rate        double precision not null,
  primary key (symbol, funding_time)
);

create table if not exists strategies (
  name        text not null,
  version     text not null,
  description text not null,
  defaults    jsonb not null,
  space       jsonb not null default '{}',
  created_at  timestamptz not null default now(),
  primary key (name, version)
);

-- Speglar research/registry.md, som förblir källan. Raderas aldrig.
create table if not exists hypotheses (
  id            text primary key,          -- H-0001
  registered_at date not null,
  registry_commit text not null,
  statement     text not null,
  track         text not null default 'A', -- A | B | C (research/tracks.md)
  decision      text check (decision in ('REJECT','MORE_RESEARCH','READY_FOR_PAPER','OGILTIG')),
  updated_at    timestamptz not null default now()
);

create table if not exists runs (
  id            uuid primary key default gen_random_uuid(),
  kind          text not null check (kind in ('registered','exploration')),  -- utforskning blir aldrig ett beslut
  hypothesis_id text references hypotheses(id),
  strategy      text not null,
  version       text not null,
  params        jsonb not null default '{}',
  run_key       text,                       -- namn@version#parameterhash
  market        text not null,
  symbol        text not null,
  interval      text not null,
  period_start  timestamptz not null,
  period_end    timestamptz not null,
  capital       double precision not null default 100000,
  costs         jsonb not null default '{"fee_bps":10,"spread_bps":2,"slippage_bps":5}',
  status        text not null default 'queued' check (status in ('queued','running','done','failed','cancelled')),
  progress      real not null default 0,
  error         text,
  created_by    uuid references auth.users(id),
  created_at    timestamptz not null default now(),
  started_at    timestamptz,
  finished_at   timestamptz,
  check (kind = 'exploration' or hypothesis_id is not null),
  check (period_end > period_start)
);
create index if not exists runs_status_created on runs (status, created_at);

create table if not exists run_results (
  run_id     uuid primary key references runs(id) on delete cascade,
  stats      jsonb not null,       -- metrics.full_stats
  criteria   jsonb,                -- bara registrerade körningar
  curves     jsonb not null,       -- equity och drawdown, nedsamplade
  windows    jsonb,                -- walk-forward per fönster
  created_at timestamptz not null default now()
);

create table if not exists run_trades (
  run_id      uuid not null references runs(id) on delete cascade,
  n           integer not null,
  side        text not null check (side in ('Long','Short')),
  entry_time  timestamptz not null,
  entry_price double precision not null,
  exit_time   timestamptz,
  exit_price  double precision,
  net_return  double precision,
  exit_reason text,
  primary key (run_id, n)
);

-- Radskydd: inloggade läser allt. Bara servern (service-nyckeln, som går förbi RLS) skriver,
-- utom att en inloggad användare får köa en utforskningskörning.
alter table candles       enable row level security;
alter table funding_rates enable row level security;
alter table strategies    enable row level security;
alter table hypotheses    enable row level security;
alter table runs          enable row level security;
alter table run_results   enable row level security;
alter table run_trades    enable row level security;

create policy read_candles     on candles       for select to authenticated using (true);
create policy read_funding     on funding_rates for select to authenticated using (true);
create policy read_strategies  on strategies    for select to authenticated using (true);
create policy read_hypotheses  on hypotheses    for select to authenticated using (true);
create policy read_runs        on runs          for select to authenticated using (true);
create policy read_results     on run_results   for select to authenticated using (true);
create policy read_trades      on run_trades    for select to authenticated using (true);

create policy queue_exploration on runs for insert to authenticated
  with check (kind = 'exploration' and status = 'queued' and created_by = auth.uid());
create policy cancel_own_run on runs for update to authenticated
  using (created_by = auth.uid() and status in ('queued','running'))
  with check (status = 'cancelled');

-- En inloggad användare får bara ändra kolumnen status (för att avbryta), inget annat.
revoke update on runs from authenticated;
grant update (status) on runs to authenticated;
