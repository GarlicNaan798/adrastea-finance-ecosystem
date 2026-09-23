"""Home dashboard: what's mine and what's next (ManageBac-style landing)."""
from datetime import date, timedelta
from html import escape

import streamlit as st

import core
import ui


def home():
    user = st.session_state.user
    uid, role = user["id"], user["role"]
    today = date.today()
    ui.page_header(f"Welcome back, {user['name'].split()[0]}", "Home",
                   f"{today:%A}, {today.day} {today:%B} · {core.ROLE_LABELS.get(role, role)}")

    projects = core.list_projects()
    latest = {r["project_id"]: r for r in core.latest_progress_by_project()}
    owned, led = core.owned_tracks(uid), core.lead_tracks(uid)
    my_tasks = [t for t in core.list_tasks(assignee_id=uid) if t["status"] != "done"]
    ums = core.upcoming_milestones()
    active = [p for p in projects if p["status"] == "active"]
    attention = [p for p in projects
                 if latest.get(p["id"], {}).get("status") in ("at_risk", "blocked")]
    week = (today + timedelta(days=7)).isoformat()
    due_soon = [t for t in my_tasks if t["due_date"] and t["due_date"][:10] <= week]

    ui.readout([("Active projects", len(active), False),
                ("My open tasks", len(my_tasks), False),
                ("Due within 7 days", len(due_soon), False),
                ("Needs attention", len(attention), bool(attention))])

    col1, col2 = st.columns(2, gap="large")
    with col1:
        ui.section("My tasks", len(my_tasks))
        if not my_tasks:
            ui.empty("Nothing assigned to you.")
        for t in my_tasks[:8]:
            if ui.row(f"mt_{t['id']}", t["title"], t["project_name"],
                      lead=ui.task_tag(t["status"]), aside=ui.due(t["due_date"])):
                ui.open_project(t["project_id"])
    with col2:
        ui.section("Upcoming deadlines", len(ums))
        if not ums:
            ui.empty("No upcoming deadlines.")
        for m in ums[:8]:
            if ui.row(f"md_{m['id']}", m["title"], m["project_name"],
                      lead=ui.due(m["due_date"])):
                ui.open_project(m["project_id"])

    st.write("")
    mine = [p for p in projects if p["director_id"] == uid
            or p["track"] in owned or p["track"] in led]
    if mine:
        ui.section("My projects", len(mine))
        for p in mine:
            lp = latest.get(p["id"])
            if ui.row(f"home_{p['id']}", p["name"], p["track"],
                      aside=(f'<span class="wide-only">{escape(lp["title"] or "")} &nbsp;</span>'
                             f'{ui.status_pill(lp["status"])}'
                             if lp else "No updates yet")):
                ui.open_project(p["id"])
        st.write("")

    feed = core.list_progress(limit=8)
    ui.section("Recent activity")
    if not feed:
        ui.empty("No updates yet.")
    for g in feed:
        if ui.row(f"act_{g['id']}", g["title"] or g["project_name"],
                  f'{g["project_name"]} · {g["author_name"] or "—"}',
                  lead=ui.status_pill(g["status"]), aside=ui.when(g["created_at"])):
            ui.open_project(g["project_id"])
