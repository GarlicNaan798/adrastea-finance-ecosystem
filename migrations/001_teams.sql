-- Additive migration: Specialist tier + per-project leads.
-- Safe to run on a populated database (no drops, no data loss).
-- Run in the Supabase SQL editor, or: psql "$DATABASE_URL" -f migrations/001_teams.sql

-- Allow the new 'specialist' role.
alter table profiles drop constraint if exists profiles_role_check;
alter table profiles add constraint profiles_role_check
    check (role in ('member','specialist','director'));

-- Per-project leads (directors assign; leads can edit their project).
create table if not exists project_leads (
    project_id bigint not null references projects(id) on delete cascade,
    user_id    uuid not null references profiles(id) on delete cascade,
    created_at text not null,
    primary key (project_id, user_id)
);
