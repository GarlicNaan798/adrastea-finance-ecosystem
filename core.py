"""Adrastea backend: Supabase Postgres (data) + Supabase Auth / GoTrue (login).

Config comes from st.secrets (or env vars) — see .streamlit/secrets.toml.example:
    SUPABASE_URL, SUPABASE_ANON_KEY, DATABASE_URL, DIRECTOR_EMAILS, FOUNDER_EMAILS
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote, urlparse

import psycopg2
import psycopg2.extras
import requests

# --- Config -----------------------------------------------------------------
CURRENCY = "$"  # one-line change for € etc.

ROLES = ("member", "director", "founder")
ROLE_LABELS = {"member": "Member", "director": "Director", "founder": "Founder"}

CATEGORIES = (
    "Personnel / Salaries", "Equipment", "Materials & Supplies", "Travel",
    "Publication / Dissemination", "Subcontracts", "Overhead / Indirect", "Other",
)

TRACKS = (
    "Bioengineering & Tech", "Health & Physiology", "Media & Marketing",
    "Policy & Advocacy", "CHASM Project",
)

PROJECT_STATUSES = ("planning", "active", "on_hold", "complete")

# Discussion-update status
PROGRESS_STATUSES = ("on_track", "at_risk", "blocked", "done")
PROGRESS_LABELS = {"on_track": "On track", "at_risk": "At risk",
                   "blocked": "Blocked", "done": "Done"}

TASK_STATUSES = ("todo", "doing", "done")
TASK_LABELS = {"todo": "To do", "doing": "In progress", "done": "Done"}


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
    d = d or date.today()
    return (d - timedelta(days=d.weekday())).isoformat()


# --- Config-driven roles ----------------------------------------------------
def _email_set(key: str) -> set[str]:
    raw = _secret(key)
    if not raw:
        return set()
    parts = re.split(r"[,;\s]+", raw) if isinstance(raw, str) else list(raw)
    return {p.strip().lower() for p in parts if p and str(p).strip()}


def director_emails() -> set[str]:
    return _email_set("DIRECTOR_EMAILS")


def founder_emails() -> set[str]:
    return _email_set("FOUNDER_EMAILS")


def owner_emails() -> set[str]:
    """Founders allowed to appoint track directors. Empty = any founder may."""
    return _email_set("OWNER_EMAILS")


def role_for_email(email: str) -> str:
    e = (email or "").strip().lower()
    if e in founder_emails():
        return "founder"
    if e in director_emails():
        return "director"
    return "member"


def track_director_emails() -> dict:
    """{track: email} from the TRACK_DIRECTORS secret (a TOML table), so a track's
    director self-configures on their login instead of a founder assigning by hand.
    Unknown tracks and blank emails are dropped; emails are lower-cased."""
    raw = _secret("TRACK_DIRECTORS")
    try:
        items = list(raw.items())
    except AttributeError:
        return {}
    return {t: str(e).strip().lower() for t, e in items
            if t in TRACKS and e and str(e).strip()}


# --- Postgres (trusted server connection; RLS bypassed by design) -----------
# The DB is a remote pooler (~1s+ per round-trip), so reads are cached briefly and
# reruns reuse them; every write clears the cache so a user sees their own change.
_pg = None


def _bust() -> None:
    try:
        import streamlit as st
        st.cache_data.clear()
    except Exception:
        pass


try:
    import streamlit as _st
    _cache = _st.cache_data(ttl=20, show_spinner=False)
except Exception:                         # offline (tests) — caching is a no-op
    def _cache(fn):
        return fn


def _conn():
    global _pg
    if _pg is None or _pg.closed:
        dsn = _secret("DATABASE_URL")
        if not dsn:
            raise RuntimeError("DATABASE_URL is not set (see secrets.toml).")
        _pg = psycopg2.connect(dsn)
        _pg.autocommit = True             # one round-trip per statement (no COMMIT RTT)
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
            if sql.lstrip()[:6].upper() in ("INSERT", "UPDATE", "DELETE"):
                _bust()                   # a write happened — drop stale read caches
            return row
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            try:
                _pg.close()
            except Exception:
                pass
            _pg = None
            if attempt == 2:
                raise


@_cache
def _q(sql, args=()):
    return [dict(r) for r in (_run(sql, args, "all") or [])]


@_cache
def _one(sql, args=()):
    r = _run(sql, args, "one")
    return dict(r) if r else None


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
    r = requests.post(_auth_url("token?grant_type=password"), headers=_auth_headers(),
                      json={"email": email.strip().lower(), "password": password},
                      timeout=15)
    return _session_from(r.json()) if r.ok else None


def refresh_session(refresh_token: str) -> dict | None:
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
    """Ensure a profile row exists; reconcile role from the allowlists on login
    (founder > director > member). Editing the allowlists takes effect next login."""
    e = (email or "").lower()
    role = role_for_email(e)
    _run("INSERT INTO profiles (id, email, name, role) VALUES (%s,%s,%s,%s) "
         "ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role, "
         "name = COALESCE(EXCLUDED.name, profiles.name)",
         (uid, e, name or email, role))
    # Self-configure track ownership: claim any UNOWNED track this user directs in
    # config. Seed-only (not overwrite), so an owner's in-app reassignment sticks
    # while a fresh/reset DB still self-heals from config.
    if role in ("director", "founder"):
        cfg = track_director_emails()
        if cfg:
            owned_now = track_directors()
            for track, demail in cfg.items():
                if demail == e and track not in owned_now:
                    set_track_director(track, uid)
    return get_profile(uid)


def list_profiles():
    return _q("SELECT * FROM profiles ORDER BY CASE role WHEN 'founder' THEN 0 "
              "WHEN 'director' THEN 1 ELSE 2 END, name")


# --- Track directors (founders assign) --------------------------------------
def set_track_director(track: str, user_id: str | None) -> None:
    """Founder action: which director owns/directs a track. None clears it."""
    if user_id is None:
        _run("DELETE FROM track_owners WHERE track = %s", (track,))
    else:
        _run("INSERT INTO track_owners (track, user_id) VALUES (%s,%s) "
             "ON CONFLICT (track) DO UPDATE SET user_id = EXCLUDED.user_id",
             (track, user_id))


def track_directors() -> dict:
    """{track: {'user_id', 'name'}} for tracks that have a director."""
    return {r["track"]: {"user_id": r["user_id"], "name": r["name"]}
            for r in _q("SELECT o.track, o.user_id, u.name FROM track_owners o "
                        "JOIN profiles u ON u.id = o.user_id")}


def owned_tracks(user_id: str) -> set:
    # Only counts if the person is still a director/founder — so removing someone
    # from the allowlist (demoted on next login) also revokes their track control.
    return {r["track"] for r in _q(
        "SELECT o.track FROM track_owners o JOIN profiles p ON p.id = o.user_id "
        "WHERE o.user_id = %s AND p.role IN ('director','founder')", (user_id,))}


# --- Track teams (directors build them from the user pool) -------------------
def add_track_member(track: str, user_id: str, is_lead: bool = False) -> None:
    _run("INSERT INTO track_members (track, user_id, is_lead, created_at) "
         "VALUES (%s,%s,%s,%s) ON CONFLICT (track, user_id) "
         "DO UPDATE SET is_lead = EXCLUDED.is_lead", (track, user_id, is_lead, now()))


def remove_track_member(track: str, user_id: str) -> None:
    _run("DELETE FROM track_members WHERE track = %s AND user_id = %s",
         (track, user_id))


def list_track_members(track: str):
    return _q("SELECT m.user_id, m.is_lead, u.name, u.email FROM track_members m "
              "JOIN profiles u ON u.id = m.user_id WHERE m.track = %s "
              "ORDER BY m.is_lead DESC, u.name", (track,))


def member_tracks(user_id: str) -> set:
    return {r["track"] for r in
            _q("SELECT track FROM track_members WHERE user_id = %s", (user_id,))}


def lead_tracks(user_id: str) -> set:
    return {r["track"] for r in
            _q("SELECT track FROM track_members WHERE user_id = %s AND is_lead",
               (user_id,))}


# --- Permissions (pure rules; pages compute the booleans once) ---------------
def can_assign_directors(role: str, email: str) -> bool:
    """Appoint/replace a track's director. Founders only — and if OWNER_EMAILS is
    set, only those founders (e.g. just the org founder). Unset → any founder,
    so a fresh install isn't locked out."""
    if role != "founder":
        return False
    owners = owner_emails()
    return not owners or (email or "").strip().lower() in owners


def can_manage_track(is_founder: bool, is_track_director: bool) -> bool:
    """Create/delete projects, budgets, build the team, assign tasks, set status
    structurally. Founder anywhere; a director only in a track they direct."""
    return is_founder or is_track_director


def can_edit_project(is_founder: bool, is_track_director: bool,
                     is_track_lead: bool) -> bool:
    """Edit a project's details/requirements/status/updates. Founder, the track's
    director, or a lead on that track."""
    return is_founder or is_track_director or is_track_lead


def can_post_update(is_founder: bool, is_track_director: bool,
                    is_track_member: bool) -> bool:
    """Post a discussion update. Founder, the track director, or any team member
    of that track (leads included)."""
    return is_founder or is_track_director or is_track_member


# --- Projects ---------------------------------------------------------------
def create_project(name, description, requirements, status, track, director_id) -> int:
    return _insert(
        "INSERT INTO projects (name, description, requirements, status, track, "
        "director_id, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (name.strip(), description, requirements, status, track, director_id, now()))


def update_project(pid, name, description, requirements, status, track) -> None:
    _run("UPDATE projects SET name=%s, description=%s, requirements=%s, status=%s, "
         "track=%s WHERE id=%s",
         (name.strip(), description, requirements, status, track, pid))


def archive_project(pid) -> None:
    """Soft-delete: hide the project but keep it (and its tasks/updates) intact."""
    _run("UPDATE projects SET archived_at = %s WHERE id = %s", (now(), pid))


def restore_project(pid) -> None:
    _run("UPDATE projects SET archived_at = NULL WHERE id = %s", (pid,))


def delete_project(pid) -> None:
    """Hard delete (cascades). Not used by the UI — reserved for tests/cleanup."""
    _run("DELETE FROM projects WHERE id = %s", (pid,))


def list_projects(status: str | None = None, track: str | None = None,
                  include_archived: bool = False):
    sql = ("SELECT p.*, u.name AS director_name FROM projects p "
           "LEFT JOIN profiles u ON u.id = p.director_id WHERE TRUE")
    args = []
    if not include_archived:
        sql += " AND p.archived_at IS NULL"
    if status:
        sql += " AND p.status = %s"; args.append(status)
    if track:
        sql += " AND p.track = %s"; args.append(track)
    return _q(sql + " ORDER BY (p.status='complete'), p.track, p.name", tuple(args))


def list_archived_projects():
    return _q("SELECT p.*, u.name AS director_name FROM projects p "
              "LEFT JOIN profiles u ON u.id = p.director_id "
              "WHERE p.archived_at IS NOT NULL ORDER BY p.archived_at DESC")


def get_project(pid: int):
    return _one("SELECT p.*, u.name AS director_name FROM projects p "
                "LEFT JOIN profiles u ON u.id = p.director_id WHERE p.id = %s", (pid,))


# --- Documents / links ------------------------------------------------------
def clean_url(url: str) -> str | None:
    u = (url or "").strip()
    p = urlparse(u)
    return u if p.scheme in ("http", "https") and p.netloc else None


def add_project_link(project_id: int, label: str, url: str, added_by: str) -> int:
    u = clean_url(url)
    if not u:
        raise ValueError("Only http(s) links are allowed.")
    return _insert(
        "INSERT INTO project_links (project_id, label, url, added_by, created_at) "
        "VALUES (%s,%s,%s,%s,%s)", (project_id, (label or u).strip(), u, added_by, now()))


def list_project_links(project_id: int):
    return _q("SELECT l.*, u.name AS added_by_name FROM project_links l "
              "LEFT JOIN profiles u ON u.id = l.added_by WHERE l.project_id = %s "
              "ORDER BY l.id", (project_id,))


def delete_project_link(link_id: int) -> None:
    _run("DELETE FROM project_links WHERE id = %s", (link_id,))


# --- Budget lines (track director / founder) --------------------------------
def set_budget_lines(project_id: int, lines: list[dict]) -> None:
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


# --- Discussion updates (title + timestamp; post any time) ------------------
def add_progress(project_id, author_id, title, status, note) -> int:
    if status not in PROGRESS_STATUSES:
        raise ValueError(status)
    return _insert(
        "INSERT INTO progress_updates (project_id, author_id, title, status, note, "
        "week_start, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (project_id, author_id, (title or "").strip(), status, note,
         week_monday(), now()))


def list_progress(project_id: int | None = None, limit: int | None = None):
    sql = ("SELECT g.*, u.name AS author_name, pr.name AS project_name, pr.track "
           "FROM progress_updates g LEFT JOIN profiles u ON u.id = g.author_id "
           "JOIN projects pr ON pr.id = g.project_id WHERE pr.archived_at IS NULL")
    args = []
    if project_id:
        sql += " AND g.project_id = %s"; args.append(project_id)
    sql += " ORDER BY g.created_at DESC, g.id DESC"
    if limit:
        sql += " LIMIT %s"; args.append(limit)
    return _q(sql, tuple(args))


def latest_progress_by_project():
    return _q(
        "SELECT DISTINCT ON (g.project_id) g.project_id, g.status, g.title, "
        "g.created_at, u.name AS author_name FROM progress_updates g "
        "LEFT JOIN profiles u ON u.id = g.author_id "
        "ORDER BY g.project_id, g.created_at DESC, g.id DESC")


# --- Tasks ------------------------------------------------------------------
def create_task(project_id, title, description, assignee_id, due_date, created_by) -> int:
    return _insert(
        "INSERT INTO tasks (project_id, title, description, assignee_id, status, "
        "due_date, created_by, created_at) VALUES (%s,%s,%s,%s,'todo',%s,%s,%s)",
        (project_id, (title or "").strip(), description, assignee_id or None,
         due_date or None, created_by, now()))


def list_tasks(project_id: int | None = None, assignee_id: str | None = None):
    sql = ("SELECT t.*, a.name AS assignee_name, pr.name AS project_name, pr.track "
           "FROM tasks t LEFT JOIN profiles a ON a.id = t.assignee_id "
           "JOIN projects pr ON pr.id = t.project_id "
           "WHERE t.archived_at IS NULL AND pr.archived_at IS NULL")
    args = []
    if project_id:
        sql += " AND t.project_id = %s"; args.append(project_id)
    if assignee_id:
        sql += " AND t.assignee_id = %s"; args.append(assignee_id)
    return _q(sql + " ORDER BY (t.status='done'), t.due_date NULLS LAST, t.id DESC",
              tuple(args))


def set_task_status(task_id: int, status: str) -> None:
    if status not in TASK_STATUSES:
        raise ValueError(status)
    _run("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))


def archive_task(task_id: int) -> None:
    _run("UPDATE tasks SET archived_at = %s WHERE id = %s", (now(), task_id))


def delete_task(task_id: int) -> None:
    """Hard delete. Not used by the UI — reserved for tests/cleanup."""
    _run("DELETE FROM tasks WHERE id = %s", (task_id,))


def add_task_link(task_id: int, label: str, url: str, added_by: str) -> int:
    u = clean_url(url)
    if not u:
        raise ValueError("Only http(s) links are allowed.")
    return _insert("INSERT INTO task_links (task_id, label, url, added_by, created_at) "
                   "VALUES (%s,%s,%s,%s,%s)",
                   (task_id, (label or u).strip(), u, added_by, now()))


def list_task_links(task_id: int):
    return _q("SELECT * FROM task_links WHERE task_id = %s ORDER BY id", (task_id,))


def delete_task_link(link_id: int) -> None:
    _run("DELETE FROM task_links WHERE id = %s", (link_id,))


# --- Milestones / deadlines (feed the calendar) -----------------------------
def add_milestone(project_id: int, title: str, due_date: str | None) -> int:
    return _insert("INSERT INTO milestones (project_id, title, due_date, created_at) "
                   "VALUES (%s,%s,%s,%s)",
                   (project_id, (title or "").strip(), due_date or None, now()))


def list_milestones(project_id: int):
    return _q("SELECT * FROM milestones WHERE project_id = %s "
              "ORDER BY (due_date IS NULL), due_date, id", (project_id,))


def toggle_milestone(mid: int, done: bool) -> None:
    _run("UPDATE milestones SET done = %s WHERE id = %s", (done, mid))


def remove_milestone(mid: int) -> None:
    _run("DELETE FROM milestones WHERE id = %s", (mid,))


def upcoming_milestones(limit: int = 8):
    return _q("SELECT m.*, pr.name AS project_name, pr.track FROM milestones m "
              "JOIN projects pr ON pr.id = m.project_id "
              "WHERE m.done = false AND m.due_date IS NOT NULL "
              "AND pr.archived_at IS NULL ORDER BY m.due_date LIMIT %s", (limit,))


# --- Comment threads (under a discussion update or a task) -------------------
def add_comment(parent_type: str, parent_id: int, author_id: str, body: str) -> int:
    if parent_type not in ("update", "task"):
        raise ValueError(parent_type)
    return _insert("INSERT INTO comments (parent_type, parent_id, author_id, body, "
                   "created_at) VALUES (%s,%s,%s,%s,%s)",
                   (parent_type, parent_id, author_id, (body or "").strip(), now()))


def list_comments(parent_type: str, parent_id: int):
    return _q("SELECT c.*, u.name AS author_name FROM comments c "
              "LEFT JOIN profiles u ON u.id = c.author_id "
              "WHERE c.parent_type = %s AND c.parent_id = %s "
              "ORDER BY c.created_at, c.id", (parent_type, parent_id))
