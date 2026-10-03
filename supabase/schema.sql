-- LunchSignal schema. Run once in the Supabase SQL editor.
-- All tables are written only from server code with the service-role key.
-- RLS is on with no policies, so the anon key can read nothing.

create table if not exists signups (
  id bigint generated always as identity primary key,
  email text not null,
  company_domain text,            -- null for freemail addresses (never clustered)
  city text,
  consent_at timestamptz not null,
  created_at timestamptz not null default now(),
  unique (email)
);
create index if not exists signups_domain_idx on signups (company_domain);

create table if not exists companies (
  domain text primary key,
  name text,
  city text,
  segment text check (segment in ('gap', 'switch', 'skip', 'unknown')),
  segment_reasons jsonb not null default '[]',
  perks jsonb not null default '[]',
  evidence jsonb not null default '[]',   -- [{url, quote}]
  ads_analysed int not null default 0,
  scan_cost_usd numeric,
  updated_at timestamptz not null default now()
);

create table if not exists job_ads (
  id bigint generated always as identity primary key,
  company_domain text not null,
  source_url text not null,
  title text,
  city text,
  extracted jsonb,                -- null when extraction failed or was rejected
  scraped_at timestamptz not null default now(),
  unique (company_domain, source_url)
);

create table if not exists alerts (
  id bigint generated always as identity primary key,
  company_domain text not null,
  kind text not null check (kind in ('demand_cluster', 'gap', 'switch', 'churn_risk')),
  payload jsonb not null default '{}',
  delivered boolean not null default false,
  created_at timestamptz not null default now(),
  unique (company_domain, kind)   -- each alert fires once per company
);

-- Company-level view only: counts, never e-mail addresses.
create or replace view demand_by_company as
select company_domain,
       count(*)::int as signups,
       array_agg(distinct city) filter (where city is not null) as cities,
       max(created_at) as last_signup_at
from signups
where company_domain is not null
group by company_domain;

alter table signups enable row level security;
alter table companies enable row level security;
alter table job_ads enable row level security;
alter table alerts enable row level security;
