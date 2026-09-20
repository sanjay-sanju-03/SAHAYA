-- SAHAYA persistent state schema.
-- Run this in Supabase SQL Editor before setting STORE_BACKEND=supabase.
-- The Render server secret key bypasses RLS; do not expose it in the frontend.

create table if not exists incidents (
  id text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists resources (
  id text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists people (
  id text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists evaluation_batches (
  id text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists group_evaluation_batches (
  id text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists route_observations (
  id text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists route_evaluations (
  id text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists audit_logs (
  id text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);

alter table incidents enable row level security;
alter table resources enable row level security;
alter table people enable row level security;
alter table evaluation_batches enable row level security;
alter table group_evaluation_batches enable row level security;
alter table route_observations enable row level security;
alter table route_evaluations enable row level security;
alter table audit_logs enable row level security;
