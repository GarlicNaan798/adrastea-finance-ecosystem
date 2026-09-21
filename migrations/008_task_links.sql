-- Additive migration: link-based attachments on tasks (like project docs).
-- Run in Supabase SQL editor or: psql "$DATABASE_URL" -f migrations/008_task_links.sql

create table if not exists task_links (
    id         bigint generated always as identity primary key,
    task_id    bigint not null references tasks(id) on delete cascade,
    label      text,
    url        text not null,
    added_by   uuid references profiles(id),
    created_at text not null
);
