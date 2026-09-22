"""Home dashboard: what's mine and what's next (ManageBac-style landing)."""
import streamlit as st

import core
import ui


def _open(pid):
    st.session_state.open_project = pid
    st.switch_page(st.session_state["_pages"]["projects"])


def home():
    user = st.session_state.user
    uid, role = user["id"], user["role"]
    ui.page_header(f"Welcome back, {user['name'].split()[0]}", "Home")
    st.caption(f"Signed in as a **{core.ROLE_LABELS.get(role, role)}**.")

    projects = core.list_projects()
    latest = {r["project_id"]: r for r in core.latest_progress_by_project()}
    owned, led = core.owned_tracks(uid), core.lead_tracks(uid)
    my_tasks = [t for t in core.list_tasks(assignee_id=uid) if t["status"] != "done"]
    active = [p for p in projects if p["status"] == "active"]
    attention = [p for p in projects
                 if latest.get(p["id"], {}).get("status") in ("at_risk", "blocked")]

    c1, c2, c3 = st.columns(3)
    c1.metric("Active projects", len(active))
    c2.metric("My open tasks", len(my_tasks))
    c3.metric("Needs attention", len(attention))

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("My tasks")
            if not my_tasks:
                st.caption("Nothing assigned to you.")
            for t in my_tasks[:8]:
                if st.button(
                    f'{core.TASK_LABELS.get(t["status"], t["status"])} · **{t["title"]}**'
                    f' · {t["project_name"]} · due {t["due_date"] or "—"}',
                        key=f"nav_mt_{t['id']}", width='stretch'):
                    _open(t["project_id"])
    with col2:
        with st.container(border=True):
            st.subheader("Upcoming deadlines")
            ums = core.upcoming_milestones()
            if not ums:
                st.caption("No upcoming deadlines.")
            for m in ums[:8]:
                if st.button(f'**{m["due_date"]}** · {m["title"]} · {m["project_name"]}',
                             key=f"nav_md_{m['id']}", width='stretch'):
                    _open(m["project_id"])

    mine = [p for p in projects if p["director_id"] == uid
            or p["track"] in owned or p["track"] in led]
    if mine:
        with st.container(border=True):
            st.subheader("My projects")
            for p in mine:
                lp = latest.get(p["id"])
                sub = (lp["title"] or core.PROGRESS_LABELS.get(lp["status"])) if lp else "no updates"
                if st.button(f'**{p["name"]}** · {p["track"]} · {sub}',
                             key=f"nav_home_{p['id']}", width='stretch'):
                    _open(p["id"])

    with st.container(border=True):
        st.subheader("Recent activity")
        feed = core.list_progress(limit=8)
        if not feed:
            st.caption("No updates yet.")
        _sc = {"on_track": "green", "at_risk": "orange", "blocked": "red", "done": "blue"}
        for g in feed:
            when = g["created_at"][:16].replace("T", " ")
            if st.button(
                f':{_sc.get(g["status"], "gray")}'
                f'[{core.PROGRESS_LABELS.get(g["status"], g["status"])}]'
                f' · **{g["title"] or g["project_name"]}** · {g["project_name"]} · {when}',
                    key=f"nav_act_{g['id']}", width='stretch'):
                _open(g["project_id"])
