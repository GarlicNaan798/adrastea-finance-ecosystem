# Migrations & data safety

**The live database is never rebuilt.** `schema.sql` is for a *fresh* install only
(it `DROP`s tables). Every change to a populated database goes through an
**additive** numbered file in `migrations/` — only `ALTER TABLE ... ADD`,
`CREATE TABLE IF NOT EXISTS`, and backfills. No `DROP` / `TRUNCATE` / destructive
`ALTER` is ever run on production data.

Apply one: paste it into the Supabase SQL editor, or
`psql "$DATABASE_URL" -f migrations/00X_name.sql`. Run each once, in order.

## Data-loss safeguards

1. **Nothing is hard-deleted from the app.** "Delete" is soft-delete (archive):
   projects and tasks get an `archived_at` timestamp, disappear from lists, and can
   be **restored**. Their children (tasks, updates, budget, links) are kept intact —
   archiving a project does **not** cascade-delete anything.
2. **Enable Supabase backups** (do this once): Supabase dashboard → Database →
   Backups. Turn on Point-in-Time Recovery (Pro plan) or rely on daily backups
   (Free). This is the ultimate net — restore the whole database to any moment.
3. **Never run `schema.sql` against production.** Use an additive migration.

## Migration log

| File | What it adds |
|------|--------------|
| `001_teams.sql` | (superseded) specialist tier + project_leads |
| `002_tracks.sql` | tracks + track-scoped leads |
| `003_links.sql` | project document links |
| `004_founders_teams_tasks.sql` | founder tier, per-track teams, discussion titles, tasks |
| `005_archive.sql` | soft-delete (archive) for projects and tasks |
