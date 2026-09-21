"""Tasks. Everyone sees their own tasks and updates status. A founder, a track's
director, and its leads assign tasks to that track's team members."""
from datetime import date

import streamlit as st

import core
import ui

st.set_page_config(page_title="Tasks · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Tasks", "Work")

uid, role = user["id"], user["role"]
is_founder = role == "founder"
owned = core.owned_tracks(uid)
led = core.lead_tracks(uid)


def can_assign(track) -> bool:
    return is_founder or track in owned or track in led


# --- My tasks ---------------------------------------------------------------
with st.container(border=True):
    st.subheader("My tasks")
    my = core.list_tasks(assignee_id=uid)
    if not my:
        st.caption("Nothing assigned to you.")
    for t in my:
        c1, c2, c3 = st.columns([3, 1.5, 1])
        c1.markdown(f'**{t["title"]}**  \n<span class="meta">{t["project_name"]} · '
                    f'due {t["due_date"] or "—"}</span>', unsafe_allow_html=True)
        ns = c2.selectbox("Status", list(core.TASK_STATUSES),
            index=list(core.TASK_STATUSES).index(t["status"]),
            format_func=lambda s: core.TASK_LABELS[s], key=f"myst_{t['id']}",
            label_visibility="collapsed")
        if c3.button("Update", key=f"myupd_{t['id']}", width='stretch',
                     disabled=(ns == t["status"])):
            core.set_task_status(t["id"], ns)
            st.rerun()

projects = core.list_projects()
assignable = [p for p in projects if can_assign(p["track"])]
if not assignable:
    st.stop()

# --- Assign a task ----------------------------------------------------------
st.subheader("Assign a task")
by_label = {f'{p["name"]} · {p["track"]}': p for p in assignable}
proj_lbl = st.selectbox("Project", list(by_label), key="task_proj")
proj = by_label[proj_lbl]
team = core.list_track_members(proj["track"])
assignees = {"— unassigned —": None} | {f'{m["name"]}': m["user_id"] for m in team}
if len(assignees) == 1:
    st.caption("This track has no team yet — add members on the Team page.")

with st.form("addtask", clear_on_submit=True):
    title = st.text_input("Task")
    desc = st.text_area("Details", height=70)
    a, b = st.columns(2)
    who = a.selectbox("Assign to", list(assignees))
    due = b.date_input("Due (optional)", value=None)
    if st.form_submit_button("Create task", type="primary", width='stretch'):
        if not title.strip():
            st.error("Add a task title.")
        else:
            core.create_task(proj["id"], title, desc, assignees[who],
                             due.isoformat() if isinstance(due, date) else None, uid)
            st.success("Task created.")
            st.rerun()

# --- Manage track tasks -----------------------------------------------------
st.subheader("Track tasks")
any_tasks = False
for p in assignable:
    tlist = core.list_tasks(project_id=p["id"])
    if not tlist:
        continue
    any_tasks = True
    st.markdown(f'**{p["name"]}**')
    for t in tlist:
        c1, c2 = st.columns([5, 1])
        c1.markdown(
            f'{t["title"]} — {core.TASK_LABELS.get(t["status"], t["status"])} · '
            f'{t["assignee_name"] or "unassigned"} · due {t["due_date"] or "—"}')
        if c2.button("Delete", key=f"deltask_{t['id']}", width='stretch'):
            core.delete_task(t["id"])
            st.rerun()
if not any_tasks:
    st.caption("No tasks yet on your tracks.")
