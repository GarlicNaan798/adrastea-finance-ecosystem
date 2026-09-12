-- Adrastea — Supabase Postgres schema.
-- Run once in the Supabase SQL editor (or `psql "$DATABASE_URL" -f schema.sql`).

-- Roles live here, keyed to Supabase Auth users. New sign-ups land as 'pending'
-- until an admin grants a real role on the Admin page.
create table if not exists profiles (
    id    uuid primary key references auth.users(id) on delete cascade,
    email text,
    name  text,
    role  text not null default 'pending'
          check (role in ('pending','director','finance','admin')),
    created_at timestamptz not null default now()
);

-- Auto-create a profile row whenever someone signs up.
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

create table if not exists projects (
    id          bigint generated always as identity primary key,
    name        text not null,
    description text,
    director_id uuid references profiles(id),
    status      text not null default 'active',
    created_at  text not null
);

create table if not exists proposals (
    id               bigint generated always as identity primary key,
    title            text not null,
    director_id      uuid not null references profiles(id),
    project_id       bigint references projects(id),
    summary          text,
    fiscal_year      text,
    status           text not null default 'draft'
                     check (status in ('draft','submitted','approved','rejected')),
    requested_amount double precision not null default 0,
    decision_note    text,
    decided_by       uuid references profiles(id),
    decided_at       text,
    created_at       text not null
);

create table if not exists budget_lines (
    id          bigint generated always as identity primary key,
    proposal_id bigint not null references proposals(id) on delete cascade,
    category    text not null,
    description text,
    amount      double precision not null default 0
);

create table if not exists transactions (
    id          bigint generated always as identity primary key,
    txn_date    text not null,
    type        text not null check (type in ('expense','income')),
    project_id  bigint references projects(id),
    category    text not null,
    description text,
    amount      double precision not null,
    recorded_by uuid references profiles(id),
    created_at  text not null
);

-- BOOTSTRAP: after you sign up in the app once, make yourself admin, e.g.
--   update profiles set role = 'admin' where email = 'you@example.org';
