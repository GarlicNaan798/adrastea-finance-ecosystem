"""Tasks. Everyone sees their own tasks and updates status. A founder, a track's
director, and its leads assign tasks to that track's team members."""
from datetime import date

import streamlit as st

import core
import ui

try:
    from streamlit_sortables import sort_items
    _HAS_BOARD = True
except Exception:
    _HAS_BOARD = False

st.set_page_config(page_title="Tasks · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Tasks", "Work")

uid, role = user["id"], user["role"]
is_founder = role == "founder"
owned = core.owned_tracks(uid)
led = core.lead_tracks(uid)


def can_assign(track) -> bool:
    return is_founder or track in owned or track in led


def attachments(task, can_edit, key_suffix=""):
    links = core.list_task_links(task["id"])
    with st.expander(f'Attachments ({len(links)})'):
        for l in links:
            a, b = st.columns([5, 1])
            a.markdown(f'[{l["label"] or l["url"]}]({l["url"]})')
            if can_edit and b.button("Remove", key=f"tlrm_{l['id']}_{key_suffix}",
                                     width='stretch'):
                core.delete_task_link(l["id"]); st.rerun()
        if can_edit:
            with st.form(f"tl_{task['id']}_{key_suffix}", clear_on_submit=True):
                fa, fb = st.columns([2, 3])
                lbl = fa.text_input("Label", placeholder="e.g. spec doc")
                u = fb.text_input("URL", placeholder="https://…")
                if st.form_submit_button("Add link"):
                    if core.clean_url(u):
                        core.add_task_link(task["id"], lbl, u, uid); st.rerun()
                    else:
                        st.error("Enter a valid http(s) URL.")
        elif not links:
            st.caption("No attachments.")


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
        attachments(t, True, "my")
        ui.comment_thread("task", t["id"], user, True, "my")

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

# --- Board: drag tasks across To-do / In progress / Done --------------------
st.subheader("Board")
btracks = sorted({p["track"] for p in assignable})
bt = st.selectbox("Track", btracks, key="board_track")
bt_tasks = [t for t in core.list_tasks() if t["track"] == bt]
_HEADERS = {"To do": "todo", "In progress": "doing", "Done": "done"}
if not bt_tasks:
    st.caption("No tasks in this track yet.")
elif not _HAS_BOARD:
    st.info("Drag board unavailable — use the list below to change status.")
else:
    by_id = {t["id"]: t for t in bt_tasks}
    cols = {h: [f'#{t["id"]} {t["title"]}' for t in bt_tasks if t["status"] == s]
            for h, s in _HEADERS.items()}
    try:
        res = sort_items(cols, multi_containers=True, direction="horizontal",
                         key=f"board_{bt}")
    except Exception:
        res = None
        st.info("Drag board unavailable — use the list below to change status.")
    if res:
        pairs = (res.items() if isinstance(res, dict)
                 else [(c.get("header"), c.get("items", [])) for c in res])
        changed = False
        for h, items in pairs:
            ns = _HEADERS.get(h)
            if not ns:
                continue
            for x in items:
                tid = int(x.split(" ", 1)[0].lstrip("#"))
                if by_id.get(tid) and by_id[tid]["status"] != ns:
                    core.set_task_status(tid, ns)
                    changed = True
        if changed:
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
        if c2.button("Archive", key=f"arctask_{t['id']}", width='stretch'):
            core.archive_task(t["id"])
            st.rerun()
        _ce = can_assign(p["track"]) or t["assignee_id"] == uid
        attachments(t, _ce, "trk")
        ui.comment_thread("task", t["id"], user, _ce, "trk")
if not any_tasks:
    st.caption("No tasks yet on your tracks.")
