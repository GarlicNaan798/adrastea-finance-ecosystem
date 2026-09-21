# Adrastea — team project tracking

A Streamlit app (Supabase backend) where a research team runs its work across
**tracks** — projects, a timestamped **discussion**, and **tasks**.

## Roles

Work is organised into five **tracks**: **Bioengineering & Tech**, **Health &
Physiology**, **Media & Marketing**, **Policy & Advocacy**, **CHASM Project**.
Each track has a director and a team. Access, most to least:

| Role | Set by | Can do |
|------|--------|--------|
| `founder`  | email in `FOUNDER_EMAILS` | global admin: assign track directors, manage any track/team/project |
| `director` | email in `DIRECTOR_EMAILS`; a founder gives them track(s) | run **their** track(s): create/delete projects, budgets, build the team, assign tasks, set status. Other tracks are view-only |
| **lead** | their track's director marks them a lead | edit that track's projects (details/requirements/status) + everything a member can |
| `member`   | any registered email a director adds to a track team | post discussion updates and work assigned tasks on their track(s); view everything |

Roles reconcile from the allowlists on every sign-in (founder > director >
member), so removing someone from an allowlist demotes them next login — and that
also revokes any track ownership they held.

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
   - `FOUNDER_EMAILS`, `DIRECTOR_EMAILS` — TOML arrays of founder / director emails
   This file is git-ignored, so keys and the allowlists are never published.
   On an already-running database, apply the additive files in
   [`migrations/`](migrations) instead of re-running `schema.sql` (which drops
   tables).
4. **Install deps**: `py -m pip install -r requirements.txt`
5. **Run**: `py -m streamlit run app.py` → http://localhost:8501
6. Everyone signs up (name, email, password). A **founder** then assigns track
   directors and each director builds their track's team (Team page).

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
