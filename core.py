"""Adrastea backend: Supabase Postgres (data) + Supabase Auth / GoTrue (login).

Config comes from st.secrets (or env vars) — see .streamlit/secrets.toml.example:
    SUPABASE_URL, SUPABASE_ANON_KEY, DATABASE_URL
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import requests

# --- Config -----------------------------------------------------------------
CURRENCY = "$"  # one-line change for € etc.

ASSIGNABLE_ROLES = ("director", "finance", "admin")  # what an admin can grant
ALL_ROLES = ("pending",) + ASSIGNABLE_ROLES

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


# --- Auth via GoTrue REST (no SDK needed for four endpoints) -----------------
def _auth_url(path: str) -> str:
    return f"{_secret('SUPABASE_URL').rstrip('/')}/auth/v1/{path}"


def _auth_headers(token: str | None = None) -> dict:
    h = {"apikey": _secret("SUPABASE_ANON_KEY"), "Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def sign_up(email: str, password: str, name: str) -> tuple[bool, str]:
    r = requests.post(_auth_url("signup"), headers=_auth_headers(),
                      json={"email": email.strip().lower(), "password": password,
                            "data": {"name": name.strip()}}, timeout=15)
    if r.ok:
        return True, ("Account created. If email confirmation is on, confirm via "
                      "the link before signing in. An admin must grant you access.")
    return False, r.json().get("msg", r.text)


def sign_in(email: str, password: str) -> dict | None:
    """Return {access_token, id, email} on success, else None."""
    r = requests.post(_auth_url("token?grant_type=password"),
                      headers=_auth_headers(),
                      json={"email": email.strip().lower(), "password": password},
                      timeout=15)
    if not r.ok:
        return None
    d = r.json()
    return {"access_token": d["access_token"], "id": d["user"]["id"],
            "email": d["user"]["email"]}


def change_password(access_token: str, new_password: str) -> tuple[bool, str]:
    r = requests.put(_auth_url("user"), headers=_auth_headers(access_token),
                     json={"password": new_password}, timeout=15)
    return (True, "Password updated.") if r.ok else (False, r.text)


def send_reset(email: str) -> None:
    requests.post(_auth_url("recover"), headers=_auth_headers(),
                  json={"email": email.strip().lower()}, timeout=15)


# --- Profiles / roles -------------------------------------------------------
def get_profile(uid: str):
    return _one("SELECT * FROM profiles WHERE id = %s", (uid,))


def list_profiles():
    return _q("SELECT * FROM profiles ORDER BY "
              "(role='pending') DESC, role, name")


def set_role(uid: str, role: str) -> None:
    if role not in ALL_ROLES:
        raise ValueError(role)
    _run("UPDATE profiles SET role = %s WHERE id = %s", (role, uid))


# --- Projects ---------------------------------------------------------------
def create_project(name, description, director_id) -> int:
    return _insert(
        "INSERT INTO projects (name, description, director_id, created_at) "
        "VALUES (%s,%s,%s,%s)", (name.strip(), description, director_id, now()))


def list_projects(director_id: str | None = None):
    if director_id:
        return _q("SELECT * FROM projects WHERE director_id = %s ORDER BY name",
                  (director_id,))
    return _q("SELECT * FROM projects ORDER BY name")


def get_project(pid: int):
    return _one("SELECT * FROM projects WHERE id = %s", (pid,))


# --- Proposals + budget lines -----------------------------------------------
def create_proposal(title, director_id, summary, fiscal_year,
                    project_id=None) -> int:
    return _insert(
        "INSERT INTO proposals (title, director_id, project_id, summary, "
        "fiscal_year, status, created_at) VALUES (%s,%s,%s,%s,%s,'draft',%s)",
        (title.strip(), director_id, project_id, summary, fiscal_year, now()))


def update_proposal(pid, title, summary, fiscal_year) -> None:
    _run("UPDATE proposals SET title=%s, summary=%s, fiscal_year=%s WHERE id=%s",
         (title, summary, fiscal_year, pid))


def set_budget_lines(proposal_id: int, lines: list[dict]) -> None:
    """Replace all budget lines; recompute requested_amount as their sum."""
    _run("DELETE FROM budget_lines WHERE proposal_id = %s", (proposal_id,))
    total = 0.0
    for ln in lines:
        amt = round(float(ln.get("amount") or 0), 2)
        if amt == 0 and not (ln.get("description") or "").strip():
            continue
        _run("INSERT INTO budget_lines (proposal_id, category, description, amount) "
             "VALUES (%s,%s,%s,%s)",
             (proposal_id, ln["category"], ln.get("description", ""), amt))
        total += amt
    _run("UPDATE proposals SET requested_amount = %s WHERE id = %s",
         (round(total, 2), proposal_id))


def list_budget_lines(proposal_id: int):
    return _q("SELECT * FROM budget_lines WHERE proposal_id = %s ORDER BY id",
              (proposal_id,))


def get_proposal(pid: int):
    return _one("SELECT * FROM proposals WHERE id = %s", (pid,))


def list_proposals(director_id: str | None = None, status: str | None = None):
    sql = ("SELECT p.*, u.name AS director_name, pr.name AS project_name "
           "FROM proposals p JOIN profiles u ON u.id = p.director_id "
           "LEFT JOIN projects pr ON pr.id = p.project_id WHERE TRUE")
    args = []
    if director_id:
        sql += " AND p.director_id = %s"; args.append(director_id)
    if status:
        sql += " AND p.status = %s"; args.append(status)
    return _q(sql + " ORDER BY p.created_at DESC", args)


def submit_proposal(pid: int) -> None:
    _run("UPDATE proposals SET status='submitted' WHERE id=%s AND status='draft'",
         (pid,))


def decide_proposal(pid: int, approve: bool, decided_by: str, note: str = "") -> None:
    p = get_proposal(pid)
    if not p:
        raise ValueError("no such proposal")
    project_id = p["project_id"]
    if approve and project_id is None:
        project_id = create_project(p["title"], p["summary"], p["director_id"])
    status = "approved" if approve else "rejected"
    _run("UPDATE proposals SET status=%s, project_id=%s, decision_note=%s, "
         "decided_by=%s, decided_at=%s WHERE id=%s",
         (status, project_id, note, decided_by, now(), pid))


# --- Transactions -----------------------------------------------------------
def create_transaction(txn_date, type_, project_id, category, description,
                       amount, recorded_by) -> int:
    if type_ not in ("expense", "income"):
        raise ValueError(type_)
    return _insert(
        "INSERT INTO transactions (txn_date, type, project_id, category, "
        "description, amount, recorded_by, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (txn_date, type_, project_id, category, description,
         round(abs(float(amount)), 2), recorded_by, now()))


def list_transactions(project_id: int | None = None):
    sql = ("SELECT t.*, pr.name AS project_name FROM transactions t "
           "LEFT JOIN projects pr ON pr.id = t.project_id")
    args = []
    if project_id:
        sql += " WHERE t.project_id = %s"; args.append(project_id)
    return _q(sql + " ORDER BY t.txn_date DESC, t.id DESC", args)


# --- Finance summaries ------------------------------------------------------
def org_totals() -> dict:
    row = _one(
        "SELECT "
        " COALESCE(SUM(amount) FILTER (WHERE type='income'),0)  AS income, "
        " COALESCE(SUM(amount) FILTER (WHERE type='expense'),0) AS expense "
        "FROM transactions")
    income, expense = row["income"], row["expense"]
    approved = _one("SELECT COALESCE(SUM(requested_amount),0) AS b "
                    "FROM proposals WHERE status='approved'")["b"]
    return {"income": income, "expense": expense, "net": income - expense,
            "approved_budget": approved}


def spend_by_category():
    return _q("SELECT category, "
              "COALESCE(SUM(amount) FILTER (WHERE type='expense'),0) AS spent "
              "FROM transactions GROUP BY category ORDER BY spent DESC")


def spend_by_project():
    return _q(
        "SELECT pr.id, pr.name, "
        " COALESCE(SUM(t.amount) FILTER (WHERE t.type='expense'),0) AS spent "
        "FROM projects pr LEFT JOIN transactions t ON t.project_id = pr.id "
        "GROUP BY pr.id, pr.name ORDER BY spent DESC")


def budget_vs_actual(project_id: int) -> list[dict]:
    budget = _q(
        "SELECT bl.category, COALESCE(SUM(bl.amount),0) AS budget "
        "FROM budget_lines bl JOIN proposals p ON p.id = bl.proposal_id "
        "WHERE p.project_id = %s AND p.status = 'approved' GROUP BY bl.category",
        (project_id,))
    actual = _q(
        "SELECT category, COALESCE(SUM(amount),0) AS spent FROM transactions "
        "WHERE project_id = %s AND type = 'expense' GROUP BY category",
        (project_id,))
    b = {r["category"]: r["budget"] for r in budget}
    a = {r["category"]: r["spent"] for r in actual}
    out = []
    for cat in sorted(set(b) | set(a), key=lambda c: (c not in CATEGORIES, c)):
        bd, sp = b.get(cat, 0.0), a.get(cat, 0.0)
        out.append({"category": cat, "budget": bd, "spent": sp,
                    "remaining": round(bd - sp, 2)})
    return out
