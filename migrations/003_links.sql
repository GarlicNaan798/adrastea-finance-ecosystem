-- Additive migration: document links on projects (Google Drive / Docs URLs).
-- Safe on a populated database. Run in Supabase SQL editor or:
--   psql "$DATABASE_URL" -f migrations/003_links.sql

create table if not exists project_links (
    id         bigint generated always as identity primary key,
    project_id bigint not null references projects(id) on delete cascade,
    label      text,
    url        text not null,
    added_by   uuid references profiles(id),
    created_at text not null
);
