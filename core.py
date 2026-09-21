"""Adrastea backend: Supabase Postgres (data) + Supabase Auth / GoTrue (login).

Config comes from st.secrets (or env vars) — see .streamlit/secrets.toml.example:
    SUPABASE_URL, SUPABASE_ANON_KEY, DATABASE_URL, DIRECTOR_EMAILS
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import psycopg2
import psycopg2.extras
import requests

# --- Config -----------------------------------------------------------------
CURRENCY = "$"  # one-line change for € etc.

ROLES = ("member", "specialist", "director")
ASSIGNABLE_TIERS = ("member", "specialist")  # what a director can set in-app
ROLE_LABELS = {"member": "Member", "specialist": "Specialist", "director": "Director"}

# Budget line categories (directors set these per project).
CATEGORIES = (
    "Personnel / Salaries",
    "Equipment",
    "Materials & Supplies",
    "Travel",
    "Publication / Dissemination",
    "Subcontracts",
    "Overhead / Indirect",
    "Other",
)

TRACKS = (
    "Bioengineering & Tech",
    "Health & Physiology",
    "Media & Marketing",
    "Policy & Advocacy",
    "CHASM Project",
)

PROJECT_STATUSES = ("planning", "active", "on_hold", "complete")
PROGRESS_STATUSES = ("on_track", "at_risk", "blocked", "done")
PROGRESS_LABELS = {"on_track": "On track", "at_risk": "At risk",
                   "blocked": "Blocked", "done": "Done"}


def _secret(key: str, default=None):
    # Env first (explicit override), then secrets.toml. Both ignore blank values,
    # so unfilled placeholders don't mask a real setting. NB: accessing st.secrets
    # copies secrets.toml into os.environ, so env-first also keeps that consistent.
    val = os.environ.get(key)
    if val:
        return val
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return val
    except Exception:
        pass
    return default


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def money(x) -> str:
    return f"{CURRENCY}{float(x or 0):,.2f}"


def week_monday(d: date | None = None) -> str:
    """ISO date of the Monday of d's week (default: this week)."""
    d = d or date.today()
    return (d - timedelta(days=d.weekday())).isoformat()


# --- Director allowlist (config-driven roles) -------------------------------
def director_emails() -> set[str]:
    """Emails designated as directors. Accepts a TOML array or a
    comma/space/semicolon-separated string in DIRECTOR_EMAILS."""
    raw = _secret("DIRECTOR_EMAILS")
    if not raw:
        return set()
    parts = re.split(r"[,;\s]+", raw) if isinstance(raw, str) else list(raw)
    return {p.strip().lower() for p in parts if p and str(p).strip()}


def role_for_email(email: str) -> str:
    return "director" if (email or "").strip().lower() in director_emails() else "member"


# --- Postgres (trusted server connection; RLS bypassed by design) -----------
_pg = None


def _conn():
    global _pg
    if _pg is None or _pg.closed:
        dsn = _secret("DATABASE_URL")
        if not dsn:
            raise RuntimeError("DATABASE_URL is not set (see secrets.toml).")
        _pg = psycopg2.connect(dsn)
    return _pg


def _run(sql: str, args=(), fetch: str | None = None):
    """Execute SQL, reconnecting once if the pooled connection went stale."""
    global _pg
    for attempt in (1, 2):
        try:
            conn = _conn()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, args)
                row = (cur.fetchone() if fetch == "one"
                       else cur.fetchall() if fetch == "all" else None)
            conn.commit()
            return row
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            try:
                _pg.close()
            except Exception:
                pass
            _pg = None
            if attempt == 2:
                raise


def _q(sql, args=()):
    return _run(sql, args, "all")


def _one(sql, args=()):
    return _run(sql, args, "one")


def _insert(sql, args=()) -> int:
    return _run(sql + " RETURNING id", args, "one")["id"]


# --- Auth via GoTrue REST (no SDK needed for these endpoints) ----------------
def _auth_url(path: str) -> str:
    return f"{_secret('SUPABASE_URL').rstrip('/')}/auth/v1/{path}"


def _auth_headers(token: str | None = None) -> dict:
    h = {"apikey": _secret("SUPABASE_ANON_KEY"), "Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _redirect_suffix() -> str:
    """Query suffix pointing email-confirmation links back at the app.
    APP_URL must also be listed in Supabase → Auth → URL Configuration."""
    url = _secret("APP_URL")
    return f"?redirect_to={quote(url, safe='')}" if url else ""


def sign_up(email: str, password: str, name: str) -> tuple[bool, str]:
    r = requests.post(_auth_url("signup") + _redirect_suffix(), headers=_auth_headers(),
                      json={"email": email.strip().lower(), "password": password,
                            "data": {"name": name.strip()}}, timeout=15)
    if r.ok:
        return True, ("Account created. If email confirmation is on, confirm via "
                      "the link, then sign in.")
    return False, r.json().get("msg", r.text)


def _session_from(d: dict) -> dict:
    return {"access_token": d["access_token"], "refresh_token": d["refresh_token"],
            "id": d["user"]["id"], "email": d["user"]["email"]}


def sign_in(email: str, password: str) -> dict | None:
    """Return {access_token, refresh_token, id, email} on success, else None."""
    r = requests.post(_auth_url("token?grant_type=password"),
                      headers=_auth_headers(),
                      json={"email": email.strip().lower(), "password": password},
                      timeout=15)
    return _session_from(r.json()) if r.ok else None


def refresh_session(refresh_token: str) -> dict | None:
    """Exchange a stored refresh token for a fresh session (rotates the token)."""
    try:
        r = requests.post(_auth_url("token?grant_type=refresh_token"),
                          headers=_auth_headers(),
                          json={"refresh_token": refresh_token}, timeout=15)
    except Exception:
        return None
    return _session_from(r.json()) if r.ok else None


def sign_out(access_token: str) -> None:
    try:
        requests.post(_auth_url("logout"), headers=_auth_headers(access_token),
                      timeout=10)
    except Exception:
        pass


def change_password(access_token: str, new_password: str) -> tuple[bool, str]:
    r = requests.put(_auth_url("user"), headers=_auth_headers(access_token),
                     json={"password": new_password}, timeout=15)
    return (True, "Password updated.") if r.ok else (False, r.text)


# --- Profiles / roles -------------------------------------------------------
def get_profile(uid: str):
    return _one("SELECT * FROM profiles WHERE id = %s", (uid,))


def sync_profile(uid: str, email: str, name: str | None = None) -> dict:
    """Ensure a profile row exists and reconcile its role on every login.

    The director allowlist always wins. Otherwise an in-app 'specialist'
    promotion is preserved; everyone else is a 'member'. (So logging in never
    silently demotes a specialist, but dropping someone from the allowlist does
    demote them from director.)"""
    prof = get_profile(uid)
    if email and email.strip().lower() in director_emails():
        role = "director"
    elif prof and prof["role"] == "specialist":
        role = "specialist"
    else:
        role = "member"
    _run("INSERT INTO profiles (id, email, name, role) VALUES (%s,%s,%s,%s) "
         "ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role, "
         "name = COALESCE(EXCLUDED.name, profiles.name)",
         (uid, (email or "").lower(), name or email, role))
    return get_profile(uid)


def set_tier(uid: str, tier: str) -> None:
    """Director action: promote/demote a person between member and specialist.
    Directors come from the allowlist and can't be set here."""
    if tier not in ASSIGNABLE_TIERS:
        raise ValueError(tier)
    _run("UPDATE profiles SET role = %s WHERE id = %s AND role <> 'director'",
         (tier, uid))


def list_profiles():
    return _q("SELECT * FROM profiles ORDER BY "
              "CASE role WHEN 'director' THEN 0 WHEN 'specialist' THEN 1 ELSE 2 END, name")


# --- Projects (directors set these) -----------------------------------------
def create_project(name, description, requirements, status, track, director_id) -> int:
    return _insert(
        "INSERT INTO projects (name, description, requirements, status, track, "
        "director_id, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (name.strip(), description, requirements, status, track, director_id, now()))


def update_project(pid, name, description, requirements, status, track) -> None:
    _run("UPDATE projects SET name=%s, description=%s, requirements=%s, status=%s, "
         "track=%s WHERE id=%s",
         (name.strip(), description, requirements, status, track, pid))


def delete_project(pid) -> None:
    _run("DELETE FROM projects WHERE id = %s", (pid,))


def list_projects(status: str | None = None, track: str | None = None):
    sql = ("SELECT p.*, u.name AS director_name FROM projects p "
           "LEFT JOIN profiles u ON u.id = p.director_id WHERE TRUE")
    args = []
    if status:
        sql += " AND p.status = %s"; args.append(status)
    if track:
        sql += " AND p.track = %s"; args.append(track)
    return _q(sql + " ORDER BY (p.status='complete'), p.track, p.name", args)


def get_project(pid: int):
    return _one("SELECT p.*, u.name AS director_name FROM projects p "
                "LEFT JOIN profiles u ON u.id = p.director_id WHERE p.id = %s", (pid,))


# --- Track leads, coordinators + permissions --------------------------------
def assign_track_lead(track: str, user_id: str) -> None:
    _run("INSERT INTO track_leads (track, user_id, created_at) VALUES (%s,%s,%s) "
         "ON CONFLICT (track, user_id) DO NOTHING", (track, user_id, now()))


def remove_track_lead(track: str, user_id: str) -> None:
    _run("DELETE FROM track_leads WHERE track = %s AND user_id = %s",
         (track, user_id))


def list_track_leads(track: str):
    return _q("SELECT tl.user_id, u.name, u.email FROM track_leads tl "
              "JOIN profiles u ON u.id = tl.user_id WHERE tl.track = %s "
              "ORDER BY u.name", (track,))


def lead_tracks(user_id: str) -> set:
    return {r["track"] for r in
            _q("SELECT track FROM track_leads WHERE user_id = %s", (user_id,))}


def set_track_coordinator(track: str, user_id: str | None) -> None:
    """Designate a track's coordinator (a director). None clears it."""
    if user_id is None:
        _run("DELETE FROM track_owners WHERE track = %s", (track,))
    else:
        _run("INSERT INTO track_owners (track, user_id) VALUES (%s,%s) "
             "ON CONFLICT (track) DO UPDATE SET user_id = EXCLUDED.user_id",
             (track, user_id))


def track_coordinators() -> dict:
    """{track: {'user_id':..., 'name':...}} for tracks that have a coordinator."""
    return {r["track"]: {"user_id": r["user_id"], "name": r["name"]}
            for r in _q("SELECT o.track, o.user_id, u.name FROM track_owners o "
                        "JOIN profiles u ON u.id = o.user_id")}


def can_edit_project_role(role: str, is_track_lead: bool) -> bool:
    """Pure permission rule for editing a project's details/requirements/status/
    progress. Directors and specialists edit any track; a member edits only
    projects in a track they lead. Budget/create/delete stay director-only."""
    return role in ("director", "specialist") or is_track_lead


# --- Budget lines (director-only, per project) ------------------------------
def set_budget_lines(project_id: int, lines: list[dict]) -> None:
    """Replace all budget lines for a project."""
    _run("DELETE FROM budget_lines WHERE project_id = %s", (project_id,))
    for ln in lines:
        amt = round(float(ln.get("amount") or 0), 2)
        if amt == 0 and not (ln.get("description") or "").strip():
            continue
        _run("INSERT INTO budget_lines (project_id, category, description, amount) "
             "VALUES (%s,%s,%s,%s)",
             (project_id, ln["category"], ln.get("description", ""), amt))


def list_budget_lines(project_id: int):
    return _q("SELECT * FROM budget_lines WHERE project_id = %s ORDER BY id",
              (project_id,))


def project_budget_total(project_id: int) -> float:
    return _one("SELECT COALESCE(SUM(amount),0) AS t FROM budget_lines "
                "WHERE project_id = %s", (project_id,))["t"]


# --- Progress updates (open posting: any member) ----------------------------
def add_progress(project_id, author_id, status, note, week_start=None) -> int:
    if status not in PROGRESS_STATUSES:
        raise ValueError(status)
    return _insert(
        "INSERT INTO progress_updates (project_id, author_id, week_start, status, "
        "note, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
        (project_id, author_id, week_start or week_monday(), status, note, now()))


def list_progress(project_id: int | None = None, limit: int | None = None):
    sql = ("SELECT g.*, u.name AS author_name, pr.name AS project_name "
           "FROM progress_updates g LEFT JOIN profiles u ON u.id = g.author_id "
           "JOIN projects pr ON pr.id = g.project_id")
    args = []
    if project_id:
        sql += " WHERE g.project_id = %s"
        args.append(project_id)
    sql += " ORDER BY g.week_start DESC, g.created_at DESC, g.id DESC"
    if limit:
        sql += " LIMIT %s"
        args.append(limit)
    return _q(sql, args)


def latest_progress_by_project():
    """Most recent update per project (for the overview at-a-glance)."""
    return _q(
        "SELECT DISTINCT ON (g.project_id) g.project_id, g.status, g.week_start, "
        "g.note, u.name AS author_name FROM progress_updates g "
        "LEFT JOIN profiles u ON u.id = g.author_id "
        "ORDER BY g.project_id, g.week_start DESC, g.created_at DESC, g.id DESC")
