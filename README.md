# Adrastea — team project tracking

A Streamlit app (Supabase backend) where a research team runs its work:

- **Directors** set the projects the team is working on — with descriptions,
  **requirements**, and a **budget breakdown** per project.
- **Everyone** posts a short **weekly progress update** (status + note) on any
  project, so the team can see at a glance what's on track, at risk, or blocked.

## Roles

Roles are assigned automatically from an email allowlist on every sign-in — no
approval step:

| Role | Set by | Can do |
|------|--------|--------|
| `director` | email is in `DIRECTOR_EMAILS` | create/edit projects, requirements and budgets; everything a member can do |
| `member`   | any other registered email | view projects and budgets; post weekly progress updates |

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
- `pages/1_Projects.py` — browse projects; directors create/edit + budget
- `pages/2_Progress.py` — post a weekly update; team timeline
- `pages/3_Account.py` — your role + change password
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
