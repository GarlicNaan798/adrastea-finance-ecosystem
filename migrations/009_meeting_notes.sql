-- 009: meeting notes. Leads/directors (and founders) post dated meeting notes
-- with a title, summary and an optional link to the full notes. Everyone reads.
-- Additive — safe to run on the live database (no data loss).
create table if not exists meeting_notes (
    id           bigint generated always as identity primary key,
    title        text not null,
    meeting_date text,             -- ISO date of the meeting
    summary      text,
    url          text,             -- optional link to the full notes
    track        text,             -- one of core.TRACKS, or null for General
    author_id    uuid references profiles(id),
    created_at   text not null
);
create index if not exists meeting_notes_by_date on meeting_notes(meeting_date desc);
