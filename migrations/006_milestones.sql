-- Additive migration: project milestones / deadlines (feed the calendar later).
-- Run in Supabase SQL editor or: psql "$DATABASE_URL" -f migrations/006_milestones.sql

create table if not exists milestones (
    id         bigint generated always as identity primary key,
    project_id bigint not null references projects(id) on delete cascade,
    title      text not null,
    due_date   text,                       -- ISO date
    done       boolean not null default false,
    created_at text not null
);
create index if not exists milestones_by_due on milestones(due_date);
