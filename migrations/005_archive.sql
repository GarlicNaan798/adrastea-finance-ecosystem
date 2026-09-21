-- Additive migration: soft-delete (archive) for projects and tasks.
-- Nothing is ever hard-deleted from the app; archived rows are hidden but kept.
-- Run in Supabase SQL editor or: psql "$DATABASE_URL" -f migrations/005_archive.sql

alter table projects add column if not exists archived_at text;
alter table tasks    add column if not exists archived_at text;
