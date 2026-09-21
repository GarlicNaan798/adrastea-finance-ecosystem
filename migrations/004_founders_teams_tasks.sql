-- Additive migration: Founder tier, retire Specialist, per-track teams,
-- discussion-update titles, and tasks. Safe on a populated database.
-- Run in Supabase SQL editor or: psql "$DATABASE_URL" -f migrations/004_founders_teams_tasks.sql

-- Roles: retire 'specialist', add 'founder'.
alter table profiles drop constraint if exists profiles_role_check;
update profiles set role = 'member' where role = 'specialist';
alter table profiles add constraint profiles_role_check
    check (role in ('member','director','founder'));

-- Per-track teams replace track_leads (which was empty).
drop table if exists track_leads cascade;
create table if not exists track_members (
    track      text not null,
    user_id    uuid not null references profiles(id) on delete cascade,
    is_lead    boolean not null default false,
    created_at text not null,
    primary key (track, user_id)
);

-- Discussion updates gain a title/brief.
alter table progress_updates add column if not exists title text;

-- Tasks.
create table if not exists tasks (
    id          bigint generated always as identity primary key,
    project_id  bigint not null references projects(id) on delete cascade,
    title       text not null,
    description text,
    assignee_id uuid references profiles(id),
    status      text not null default 'todo' check (status in ('todo','doing','done')),
    due_date    text,
    created_by  uuid references profiles(id),
    created_at  text not null
);
create index if not exists tasks_by_assignee on tasks(assignee_id);
