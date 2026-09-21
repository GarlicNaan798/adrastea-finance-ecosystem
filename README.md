# Adrastea — team project tracking

A Streamlit app (Supabase backend) where a research team runs its work:

- **Directors** set the projects the team is working on — with descriptions,
  **requirements**, and a **budget breakdown** per project.
- **Everyone** posts a short **weekly progress update** (status + note) on any
  project, so the team can see at a glance what's on track, at risk, or blocked.

## Roles

Tiers, from most to least access:

| Role | Set by | Can do |
|------|--------|--------|
| `director`   | email is in `DIRECTOR_EMAILS` | everything: create/delete projects, set budgets, assign leads, promote specialists |
| `specialist` | a director promotes them (Team page) | edit **any** project's details, requirements, status and progress (not budgets) |
| `member`     | any other registered email | view projects/budgets, post weekly progress |
| **lead** | a director assigns them to a **track** (Team page) | *(per-track hat, on top of their tier)* edit any project **in that track** — details, requirements, status and progress |

Directors and specialists are reconciled on every sign-in; a specialist promotion
is preserved across logins, and removing someone from `DIRECTOR_EMAILS` demotes
them on their next sign-in.

### Tracks

Projects belong to one of five tracks: **Bioengineering & Tech**, **Health &
Physiology**, **Media & Marketing**, **Policy & Advocacy**, and **CHASM Project**.
Each track can have a **coordinator** (a director) and its own **leads**. Directors
and specialists work across all tracks; leads work only within their track(s).

## Get the app

```bash
git clone https://github.com/GarlicNaan798/adrastea-finance-ecosystem.git
cd adrastea-finance-ecosystem
```

## One-time setup

1. **Create a Supabase project** (free tier is fine) at supabase.com; set a
   database password.
2. **Apply the schema** — open the Supabase SQL editor and run [`schema.sql`](schema.sql).
3. **Add secrets** — copy `.streamlit/secrets.toml.example` to
   `.streamlit/secrets.toml` and fill in:
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY` (Supabase → Settings → API)
   - `DATABASE_URL` (Supabase → Connect → **Session pooler** URI; replace the
     password placeholder)
   - `DIRECTOR_EMAILS` — a TOML array of the directors' emails
   This file is git-ignored, so keys and the director list are never published.
4. **Install deps**: `py -m pip install -r requirements.txt`
5. **Run**: `py -m streamlit run app.py` → http://localhost:8501
6. Everyone signs up (name, email, password). Anyone whose email is in
   `DIRECTOR_EMAILS` becomes a director on their next sign-in; everyone else is a
   member.

> Tip: In Supabase → Authentication → Email, turn **off** "Confirm email" for a
> smoother internal-team signup (or keep it on and confirm via the link).

## How it works

```
director  ──>  Project (description, requirements, budget breakdown)
                   │
member/director ──>  weekly progress update (status + note)  ──>  Timeline
                   │
                Overview: active projects · updated this week · needs attention
```

## Layout

- `app.py` — overview (projects at a glance + recent progress)
- `pages/1_Projects.py` — browse projects; directors create/edit/budget; specialists & leads edit details; attach document links (Google Drive / Docs)
- `pages/2_Progress.py` — post a weekly update; team timeline
- `pages/3_Account.py` — your role + change password
- `pages/4_Team.py` — directors promote members ↔ specialists
- `migrations/` — additive SQL migrations for an already-populated database
- `core.py` — Postgres data access, GoTrue auth, director allowlist
- `schema.sql` — Supabase Postgres schema (run once)
- `tests/test_core.py` — offline checks; `tests/smoke_live.py` — live end-to-end

## Sessions

Login persists across hard refreshes: the Supabase refresh token is stored in a
git-ignored browser cookie (`adr_session`, 30 days) and used to restore the
session on load. Sign out clears it. The cookie layer is fail-safe — if it's
unavailable the app falls back to signing in each visit.

## Design & accessibility

- **Light + dark mode**, both brand-warm, via native Streamlit theming
  (`.streamlit/config.toml` `[theme.light]` / `[theme.dark]`); follows the
  viewer's system preference.
- **WCAG AA contrast** across text, links, buttons, muted labels, and status
  pills in both themes (validated); visible keyboard focus rings on every
  interactive element; status is conveyed by label text, not colour alone.
- Fonts (Fraunces headings, Inter body) are set through native theme options, so
  Material icons render as glyphs rather than ligature text.

## Deploy (later)

Push to GitHub and deploy on [Streamlit Community Cloud](https://share.streamlit.io):
point it at `app.py`, and paste the same secrets into the app's Secrets settings.
Data persists in Supabase across restarts.
