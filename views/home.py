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
                st.markdown(
                    f'{core.TASK_LABELS.get(t["status"], t["status"])} · **{t["title"]}** '
                    f'<span class="meta">· {t["project_name"]} · due {t["due_date"] or "—"}'
                    f'</span>', unsafe_allow_html=True)
    with col2:
        with st.container(border=True):
            st.subheader("Upcoming deadlines")
            ums = core.upcoming_milestones()
            if not ums:
                st.caption("No upcoming deadlines.")
            for m in ums[:8]:
                st.markdown(f'**{m["due_date"]}** · {m["title"]} '
                            f'<span class="meta">· {m["project_name"]}</span>',
                            unsafe_allow_html=True)

    mine = [p for p in projects if p["director_id"] == uid
            or p["track"] in owned or p["track"] in led]
    if mine:
        with st.container(border=True):
            st.subheader("My projects")
            for p in mine:
                a, b = st.columns([5, 1])
                lp = latest.get(p["id"])
                a.markdown(
                    f'**{p["name"]}** <span class="meta">· {p["track"]} · '
                    f'{(lp["title"] or core.PROGRESS_LABELS.get(lp["status"])) if lp else "no updates"}'
                    f'</span>', unsafe_allow_html=True)
                if b.button("Open", key=f"home_open_{p['id']}", width='stretch'):
                    _open(p["id"])

    with st.container(border=True):
        st.subheader("Recent activity")
        feed = core.list_progress(limit=8)
        if not feed:
            st.caption("No updates yet.")
        for g in feed:
            when = g["created_at"][:16].replace("T", " ")
            st.markdown(
                f'{ui.status_pill(g["status"])} &nbsp;**{g["title"] or g["project_name"]}** '
                f'<span class="meta">· {g["project_name"]} · {when} · '
                f'{g["author_name"] or "—"}</span>', unsafe_allow_html=True)
