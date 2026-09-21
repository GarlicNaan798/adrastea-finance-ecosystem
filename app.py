"""Adrastea — team project tracking. Overview. Run: streamlit run app.py"""
import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()

ui.page_header("Overview", "Adrastea · team projects")
st.caption(f"Welcome back, {user['name'].split()[0]}. "
           f"You're signed in as a **{core.ROLE_LABELS.get(user['role'], user['role'])}**.")

projects = core.list_projects()
latest = {r["project_id"]: r for r in core.latest_progress_by_project()}
this_week = core.week_monday()

active = [p for p in projects if p["status"] == "active"]
updated_this_week = sum(1 for r in latest.values() if r["week_start"] == this_week)
attention = [p for p in projects
             if latest.get(p["id"], {}).get("status") in ("at_risk", "blocked")]

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    c1.metric("Active projects", len(active))
    c2.metric("Updated this week", updated_this_week)
    c3.metric("Needs attention", len(attention))

if not projects:
    st.info("No projects yet. " + ("Create one on the **Projects** page."
            if user["role"] == "director" else
            "A director will set up projects here soon."))
    st.stop()

def _row(p):
    lp = latest.get(p["id"])
    return {
        "Project": p["name"],
        "Track": p["track"] or "—",
        "Status": p["status"].replace("_", " ").title(),
        "Latest update": (core.PROGRESS_LABELS.get(lp["status"]) + f" · {lp['week_start']}")
        if lp else "— no updates —",
    }


# --- My projects: what I direct, coordinate, or lead ------------------------
my_tracks = core.lead_tracks(user["id"])
coordinated = {t for t, i in core.track_coordinators().items()
               if i["user_id"] == user["id"]}
mine = [p for p in projects if p["director_id"] == user["id"]
        or p["track"] in my_tracks or p["track"] in coordinated]
if mine:
    with st.container(border=True):
        st.subheader("My projects")
        st.caption("Projects you direct, coordinate, or lead.")
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
        st.subheader("Recent progress")
        feed = core.list_progress(limit=8)
        if not feed:
            st.caption("No updates yet — post one on the **Progress** page.")
        for g in feed:
            st.markdown(
                f'{ui.status_pill(g["status"])} &nbsp;**{g["project_name"]}** '
                f'<span class="meta">· {g["week_start"]} · '
                f'{g["author_name"] or "—"}</span>', unsafe_allow_html=True)
            if g["note"]:
                st.caption(g["note"])
