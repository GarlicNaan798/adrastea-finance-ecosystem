# Adrastea — research funding & finance ecosystem

A single Streamlit app for a research non-profit, backed by **Supabase**
(Postgres for data, Supabase Auth for login):

1. **Funding proposals** — team directors submit proposals with a line-item
   **budget breakdown** (category + how the money is spent). Finance/admin
   review and approve/reject.
2. **Finance & budget tracking** — approved proposals automatically become
   funded **projects** whose budgets feed an org-wide tracker: record
   income/expenses, see spending by category and project, and **budget vs.
   actual** per project.

## Roles

New sign-ups start as **pending** (no access) until an admin grants a role.

| Role | Can do |
|------|--------|
| `pending`  | Just signed up; waiting for an admin to grant access |
| `director` | Create projects, write & submit proposals with budgets, log expenses against **their own** projects |
| `finance`  | Review/approve/reject proposals, record any transaction (incl. income & org-general), full dashboards |
| `admin`    | Everything above **+ assign roles** to people |

## Get the app

```bash
git clone https://github.com/GarlicNaan798/adrastea-finance-ecosystem.git
cd adrastea-finance-ecosystem
```

## One-time setup

1. **Create a Supabase project** (free tier is fine) at supabase.com.
2. **Apply the schema** — open the Supabase SQL editor and run [`schema.sql`](schema.sql)
   (or `psql "$DATABASE_URL" -f schema.sql`).
3. **Add secrets** — copy `.streamlit/secrets.toml.example` to
   `.streamlit/secrets.toml` and fill in `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
   and `DATABASE_URL` (all from Supabase → Project Settings). This file is
   git-ignored.
4. **Install deps**: `py -m pip install -r requirements.txt`
5. **Run**: `py -m streamlit run app.py` → open http://localhost:8501
6. **Make yourself admin**: sign up in the app once, then in the Supabase SQL
   editor run
   `update profiles set role = 'admin' where email = 'you@example.org';`
   Now you can grant roles to everyone else from the **Admin** page.

> Tip: In Supabase → Authentication → Providers → Email, turn **off** "Confirm
> email" for a smoother internal-team signup (or keep it on and confirm links).

## How the two halves connect

```
director writes proposal ──> budget_lines (category, how spent, amount)
        │  submit
        ▼
finance approves  ──> a funded Project is created & the budget is attached
        │
        ▼
finance/director records transactions on the project
        │
        ▼
Projects page: budget vs. actual per category   ·   Finance page: org dashboards
```

## Layout

- `app.py` — login + org overview
- `pages/1_Proposals.py` — write/submit proposals, review queue
- `pages/2_Projects.py` — per-project budget vs. actual
- `pages/3_Finance.py` — record transactions + org dashboards
- `pages/4_Admin.py` — change your password; admins assign roles
- `core.py` — Postgres data access + GoTrue auth (REST)
- `schema.sql` — Supabase Postgres schema (run once)
- `tests/test_core.py` — offline checks (`py tests/test_core.py`)
- `tests/smoke_live.py` — live end-to-end budget check against your Supabase

## Deploy (later)

Push to GitHub and deploy on [Streamlit Community Cloud](https://share.streamlit.io):
point it at `app.py`, and paste the same three secrets into the app's Secrets
settings. Data persists in Supabase across restarts.

## Sessions

Login persists across hard refreshes: on sign-in the Supabase **refresh token**
is stored in a browser cookie (`adr_session`, 30 days) and used to restore the
session on load. Sign out clears the cookie and revokes the token. The cookie
layer is fail-safe — if it's unavailable the app simply falls back to signing in
each visit. The token cookie is readable by page scripts, so keep the app's HTML
trusted (it only ever renders first-party markup).
