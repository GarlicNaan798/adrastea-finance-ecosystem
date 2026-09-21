-- Adrastea — team project tracking schema (Supabase Postgres).
-- Run once in the Supabase SQL editor (or `psql "$DATABASE_URL" -f schema.sql`).
-- This rebuilds the app tables. It is safe on a fresh project; it DROPS the
-- app tables (and their data) if you re-run it on a populated database.

drop table if exists progress_updates cascade;
drop table if exists project_leads cascade;
drop table if exists budget_lines cascade;
drop table if exists projects cascade;
-- legacy tables from the previous (finance) version, if present:
drop table if exists transactions cascade;
drop table if exists proposals cascade;
drop table if exists profiles cascade;

-- People. Role is derived from the director allowlist at login (see core.py);
-- new sign-ups default to 'member'.
create table profiles (
    id    uuid primary key references auth.users(id) on delete cascade,
    email text,
    name  text,
    role  text not null default 'member'
          check (role in ('member','specialist','director')),
    created_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    insert into public.profiles (id, email, name)
    values (new.id, new.email, coalesce(new.raw_user_meta_data->>'name', new.email))
    on conflict (id) do nothing;
    return new;
end; $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- Projects: set by directors (name, description, requirements, budget).
create table projects (
    id           bigint generated always as identity primary key,
    name         text not null,
    description  text,
    requirements text,
    status       text not null default 'active'
                 check (status in ('planning','active','on_hold','complete')),
    director_id  uuid references profiles(id),
    created_at   text not null
);

-- Director-only budget breakdown, one row per line item.
create table budget_lines (
    id          bigint generated always as identity primary key,
    project_id  bigint not null references projects(id) on delete cascade,
    category    text not null,
    description text,
    amount      double precision not null default 0
);

-- Weekly progress updates; any registered member may post (open posting).
create table progress_updates (
    id         bigint generated always as identity primary key,
    project_id bigint not null references projects(id) on delete cascade,
    author_id  uuid references profiles(id),
    week_start text not null,   -- ISO date of that week's Monday
    status     text not null check (status in ('on_track','at_risk','blocked','done')),
    note       text,
    created_at text not null
);
create index if not exists progress_by_project on progress_updates(project_id, week_start desc);

-- Per-project leads. Directors assign these; a lead can edit their project's
-- details/requirements/status/progress (not the budget).
create table project_leads (
    project_id bigint not null references projects(id) on delete cascade,
    user_id    uuid not null references profiles(id) on delete cascade,
    created_at text not null,
    primary key (project_id, user_id)
);
