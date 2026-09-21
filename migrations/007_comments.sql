-- Additive migration: comment threads under discussion updates and tasks.
-- Run in Supabase SQL editor or: psql "$DATABASE_URL" -f migrations/007_comments.sql

create table if not exists comments (
    id          bigint generated always as identity primary key,
    parent_type text not null check (parent_type in ('update','task')),
    parent_id   bigint not null,
    author_id   uuid references profiles(id),
    body        text not null,
    created_at  text not null
);
create index if not exists comments_by_parent on comments(parent_type, parent_id);
