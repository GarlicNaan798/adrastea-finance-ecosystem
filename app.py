"""Adrastea — team project tracking. Overview. Run: streamlit run app.py"""
import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
uid, role = user["id"], user["role"]

ui.page_header("Overview", "Adrastea · team projects")
st.caption(f"Welcome back, {user['name'].split()[0]}. "
           f"You're signed in as a **{core.ROLE_LABELS.get(role, role)}**.")

projects = core.list_projects()
latest = {r["project_id"]: r for r in core.latest_progress_by_project()}
owned = core.owned_tracks(uid)
led = core.lead_tracks(uid)
my_tasks = [t for t in core.list_tasks(assignee_id=uid) if t["status"] != "done"]

active = [p for p in projects if p["status"] == "active"]
attention = [p for p in projects
             if latest.get(p["id"], {}).get("status") in ("at_risk", "blocked")]

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    c1.metric("Active projects", len(active))
    c2.metric("My open tasks", len(my_tasks))
    c3.metric("Needs attention", len(attention))

if my_tasks:
    with st.container(border=True):
        st.subheader("My tasks")
        st.dataframe(pd.DataFrame([{
            "Task": t["title"], "Project": t["project_name"],
            "Status": core.TASK_LABELS.get(t["status"], t["status"]),
            "Due": t["due_date"] or "—"} for t in my_tasks]),
            hide_index=True, width='stretch')
    st.write("")

ums = core.upcoming_milestones()
if ums:
    with st.container(border=True):
        st.subheader("Upcoming deadlines")
        st.dataframe(pd.DataFrame([{
            "Milestone": m["title"], "Project": m["project_name"],
            "Track": m["track"] or "—", "Due": m["due_date"]} for m in ums]),
            hide_index=True, width='stretch')
    st.write("")

if not projects:
    st.info("No projects yet." + (" Create one on the **Projects** page."
            if (role == "founder" or owned) else ""))
    st.stop()


def _row(p):
    lp = latest.get(p["id"])
    return {"Project": p["name"], "Track": p["track"] or "—",
            "Status": p["status"].replace("_", " ").title(),
            "Latest update": (lp["title"] or core.PROGRESS_LABELS.get(lp["status"]))
            if lp else "— no updates —"}


mine = [p for p in projects if p["director_id"] == uid
        or p["track"] in owned or p["track"] in led]
if mine:
    with st.container(border=True):
        st.subheader("My projects")
        st.caption("Projects you direct or lead.")
        st.dataframe(pd.DataFrame([_row(p) for p in mine]),
                     hide_index=True, width='stretch')
    st.write("")

col_a, col_b = st.columns([1.1, 1])
with col_a:
    with st.container(border=True):
        st.subheader("Projects at a glance")
        st.dataframe(pd.DataFrame([_row(p) for p in projects]),
                     hide_index=True, width='stretch')
with col_b:
    with st.container(border=True):
        st.subheader("Recent discussion")
        feed = core.list_progress(limit=8)
        if not feed:
            st.caption("No updates yet — post one on the **Discussion** page.")
        for g in feed:
            when = g["created_at"][:16].replace("T", " ")
            st.markdown(
                f'{ui.status_pill(g["status"])} &nbsp;**{g["title"] or g["project_name"]}** '
                f'<span class="meta">· {g["project_name"]} · {when} · '
                f'{g["author_name"] or "—"}</span>', unsafe_allow_html=True)
            if g["note"]:
                st.caption(g["note"])
