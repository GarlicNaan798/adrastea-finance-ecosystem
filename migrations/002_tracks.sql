-- Additive migration: tracks + track-scoped leads + track coordinators.
-- Safe on a populated database. Run in Supabase SQL editor or:
--   psql "$DATABASE_URL" -f migrations/002_tracks.sql

-- Every project belongs to a track (one of core.TRACKS; validated in the app).
alter table projects add column if not exists track text;

-- Leads are now per-track, not per-project. Replace the (empty) project_leads.
drop table if exists project_leads cascade;

create table if not exists track_leads (
    track      text not null,
    user_id    uuid not null references profiles(id) on delete cascade,
    created_at text not null,
    primary key (track, user_id)
);

create table if not exists track_owners (
    track   text primary key,
    user_id uuid not null references profiles(id) on delete cascade
);
