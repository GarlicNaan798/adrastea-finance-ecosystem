"""Projects: a list grouped by track, and a per-project workspace with tabs
(Stream / Tasks / Deadlines / Docs / Budget / About) — the ManageBac 'class' model.
Everything about a project lives in one place instead of scattered global pages."""
from datetime import date

import pandas as pd
import streamlit as st

import core
import ui

try:
    from streamlit_sortables import sort_items
    _HAS_BOARD = True
except Exception:
    _HAS_BOARD = False

_BOARD = {"To do": "todo", "In progress": "doing", "Done": "done"}


def projects():
    """Router: show the open project's workspace, else the list."""
    user = st.session_state.user
    pid = st.session_state.get("open_project")
    proj = core.get_project(pid) if pid else None
    if proj and proj.get("archived_at") is None:
        _workspace(user, proj)
    else:
        st.session_state.pop("open_project", None)
        _list(user)


# --- List -------------------------------------------------------------------
def _list(user):
    uid, role = user["id"], user["role"]
    is_founder = role == "founder"
    owned = core.owned_tracks(uid)
    directors = core.track_directors()
    manageable = list(core.TRACKS) if is_founder else sorted(owned)

    def manages(track):
        return is_founder or track in owned

    ui.page_header("Projects", "Portfolio")

    if manageable:
        with st.expander("➕ New project"):
            _new_project(user, manageable)

    projects = core.list_projects()
    if not projects:
        st.info("No projects yet."
                + (" Create one above." if manageable else " Ask a director to add one."))
    else:
        present = [t for t in core.TRACKS if any(p["track"] == t for p in projects)]
        for track in present:
            st.markdown(f"#### {track}")
            st.caption(f'Director: {directors.get(track, {}).get("name") or "—"}')
            for p in [p for p in projects if p["track"] == track]:
                if st.button(f'**{p["name"]}**  ·  '
                             f'{p["status"].replace("_", " ").title()}',
                             key=f"nav_open_{p['id']}", width='stretch'):
                    st.session_state.open_project = p["id"]
                    st.rerun()

    arch = [a for a in core.list_archived_projects() if manages(a["track"])]
    if arch:
        with st.expander("Archived projects (restore)"):
            for a in arch:
                r1, r2 = st.columns([4, 1])
                r1.write(f'{a["name"]} · {a["track"]}')
                if r2.button("Restore", key=f"rest_{a['id']}", width='stretch'):
                    core.restore_project(a["id"])
                    st.rerun()


def _new_project(user, manageable):
    with st.form("newproj", clear_on_submit=True):
        name = st.text_input("Name")
        c1, c2 = st.columns(2)
        track = c1.selectbox("Track", manageable)
        status = c2.selectbox("Status", list(core.PROJECT_STATUSES), index=1,
                              format_func=lambda s: s.replace("_", " ").title())
        desc = st.text_area("Description", height=80)
        reqs = st.text_area("Requirements", height=90)
        if st.form_submit_button("Create project", type="primary", width='stretch'):
            if not name.strip():
                st.error("Add a project name.")
            else:
                pid = core.create_project(name, desc, reqs, status, track, user["id"])
                st.session_state.open_project = pid
                st.rerun()


# --- Workspace --------------------------------------------------------------
def _workspace(user, proj):
    uid, role = user["id"], user["role"]
    is_founder = role == "founder"
    track = proj["track"]
    owned, led = core.owned_tracks(uid), core.lead_tracks(uid)
    member_of = core.member_tracks(uid)
    manages = is_founder or track in owned          # budget, archive, move track
    can_edit = manages or track in led              # details, deadlines, docs, tasks
    can_post = manages or track in member_of        # stream updates

    if st.button("← All projects"):
        st.session_state.pop("open_project", None)
        st.rerun()
    ui.page_header(proj["name"], track)
    directors = core.track_directors()
    leads = ", ".join(m["name"] for m in core.list_track_members(track)
                      if m["is_lead"]) or "—"
    st.caption(f'{proj["status"].replace("_", " ").title()} · '
               f'Director: {directors.get(track, {}).get("name") or "—"} · Leads: {leads}')

    updates, tasks, deadlines, docs, budget, about = st.tabs(
        ["Updates", "Tasks", "Deadlines", "Docs", "Budget", "About"])
    with updates:
        _stream(user, proj, can_post)
    with tasks:
        _tasks(user, proj, can_edit)
    with deadlines:
        _deadlines(proj, can_edit)
    with docs:
        _docs(user, proj, can_edit)
    with budget:
        _budget(proj, manages)
    with about:
        _about(user, proj, can_edit, manages)


def _stream(user, proj, can_post):
    pid = proj["id"]
    if can_post:
        with st.form("post", clear_on_submit=True):
            c1, c2 = st.columns([3, 1.4])
            title = c1.text_input("Update", placeholder="e.g. Sensor array wired up")
            status = c2.selectbox("Status", list(core.PROGRESS_STATUSES),
                                  format_func=lambda s: core.PROGRESS_LABELS[s])
            note = st.text_area("Details", height=80)
            if st.form_submit_button("Post update", type="primary", width='stretch'):
                if not title.strip():
                    st.error("Add a short title.")
                else:
                    core.add_progress(pid, user["id"], title, status, note.strip())
                    st.rerun()
    else:
        st.caption("Ask to join this track's team to post updates.")
    feed = core.list_progress(project_id=pid, limit=200)
    st.markdown(f"#### Update history ({len(feed)})")
    st.caption("Every update on this project, newest first — visible to everyone.")
    if not feed:
        st.caption("No updates yet.")
    for g in feed:
        when = g["created_at"][:16].replace("T", " ")
        st.markdown(
            f'{ui.status_pill(g["status"])} &nbsp;**{g["title"] or "(untitled)"}** '
            f'<span class="meta">· {when} · {g["author_name"] or "—"}</span>',
            unsafe_allow_html=True)
        if g["note"]:
            st.write(g["note"])
        ui.comment_thread("update", g["id"], user, can_post)
        st.divider()


def _task_links(task, can_edit, uid):
    links = core.list_task_links(task["id"])
    with st.expander(f"Attachments ({len(links)})"):
        for l in links:
            a, b = st.columns([5, 1])
            a.markdown(f'[{l["label"] or l["url"]}]({l["url"]})')
            if can_edit and b.button("Remove", key=f"tlrm_{l['id']}", width='stretch'):
                core.delete_task_link(l["id"])
                st.rerun()
        if can_edit:
            with st.form(f"tl_{task['id']}", clear_on_submit=True):
                fa, fb = st.columns([2, 3])
                lbl = fa.text_input("Label", placeholder="e.g. spec doc")
                u = fb.text_input("URL", placeholder="https://…")
                if st.form_submit_button("Add link"):
                    if core.clean_url(u):
                        core.add_task_link(task["id"], lbl, u, uid)
                        st.rerun()
                    else:
                        st.error("Enter a valid http(s) URL.")
        elif not links:
            st.caption("No attachments.")


def _tasks(user, proj, can_assign):
    uid, pid = user["id"], proj["id"]
    if can_assign:
        team = core.list_track_members(proj["track"])
        assignees = {"— unassigned —": None} | {m["name"]: m["user_id"] for m in team}
        with st.form("addtask", clear_on_submit=True):
            title = st.text_input("Task")
            desc = st.text_area("Details", height=68)
            a, b = st.columns(2)
            who = a.selectbox("Assign to", list(assignees))
            due = b.date_input("Due (optional)", value=None)
            if st.form_submit_button("Create task", type="primary", width='stretch'):
                if not title.strip():
                    st.error("Add a task title.")
                else:
                    core.create_task(pid, title, desc, assignees[who],
                                     due.isoformat() if isinstance(due, date) else None, uid)
                    st.rerun()
        if len(assignees) == 1:
            st.caption("No team on this track yet — add members on the Team page.")

    tlist = core.list_tasks(project_id=pid)
    if tlist and _HAS_BOARD and can_assign:
        by_id = {t["id"]: t for t in tlist}
        cols = {h: [f'#{t["id"]} {t["title"]}' for t in tlist if t["status"] == s]
                for h, s in _BOARD.items()}
        try:
            res = sort_items(cols, multi_containers=True, direction="horizontal",
                             key=f"board_{pid}")
        except Exception:
            res = None
        if res:
            pairs = (res.items() if isinstance(res, dict)
                     else [(c.get("header"), c.get("items", [])) for c in res])
            changed = False
            for h, items in pairs:
                ns = _BOARD.get(h)
                if not ns:
                    continue
                for x in items:
                    tid = int(x.split(" ", 1)[0].lstrip("#"))
                    if by_id.get(tid) and by_id[tid]["status"] != ns:
                        core.set_task_status(tid, ns)
                        changed = True
            if changed:
                st.rerun()
    elif not tlist:
        st.caption("No tasks yet.")

    for t in tlist:
        can_e = can_assign or t["assignee_id"] == uid   # its assignee, or a manager/lead
        c1, c2, c3 = st.columns([3, 1.5, 1])
        c1.markdown(f'**{t["title"]}** <span class="meta">· '
                    f'{t["assignee_name"] or "unassigned"} · due {t["due_date"] or "—"}'
                    f'</span>', unsafe_allow_html=True)
        ns = c2.selectbox("Status", list(core.TASK_STATUSES),
                          index=list(core.TASK_STATUSES).index(t["status"]),
                          format_func=lambda s: core.TASK_LABELS[s],
                          key=f"tst_{t['id']}", label_visibility="collapsed",
                          disabled=not can_e)
        if can_e and ns != t["status"]:
            core.set_task_status(t["id"], ns)
            st.rerun()
        if can_assign and c3.button("Archive", key=f"arc_{t['id']}", width='stretch'):
            core.archive_task(t["id"])
            st.rerun()
        _task_links(t, can_e, uid)
        ui.comment_thread("task", t["id"], user, can_e)
        st.divider()


def _deadlines(proj, can_edit):
    pid = proj["id"]
    ms = core.list_milestones(pid)
    if not ms:
        st.caption("No milestones yet.")
    for m in ms:
        c1, c2 = st.columns([5, 1])
        done = c1.checkbox(f'{m["title"]} · {m["due_date"] or "no date"}',
                           value=m["done"], key=f"ms_{m['id']}", disabled=not can_edit)
        if can_edit and done != m["done"]:
            core.toggle_milestone(m["id"], done)
            st.rerun()
        if can_edit and c2.button("Remove", key=f"msrm_{m['id']}", width='stretch'):
            core.remove_milestone(m["id"])
            st.rerun()
    if can_edit:
        with st.form(f"addms_{pid}", clear_on_submit=True):
            g1, g2 = st.columns([3, 2])
            mt = g1.text_input("Milestone")
            md = g2.date_input("Due (optional)", value=None)
            if st.form_submit_button("Add milestone"):
                if mt.strip():
                    core.add_milestone(pid, mt,
                                       md.isoformat() if isinstance(md, date) else None)
                    st.rerun()
                else:
                    st.error("Add a milestone title.")


def _docs(user, proj, can_edit):
    pid = proj["id"]
    st.caption("Attach Google Drive / Docs links (or any URL).")
    for l in core.list_project_links(pid):
        a, b = st.columns([5, 1])
        a.markdown(f'[{l["label"] or l["url"]}]({l["url"]})')
        if can_edit and b.button("Remove", key=f"rml_{l['id']}", width='stretch'):
            core.delete_project_link(l["id"])
            st.rerun()
    if can_edit:
        with st.form(f"addlink_{pid}", clear_on_submit=True):
            fa, fb = st.columns([2, 3])
            lbl = fa.text_input("Label", placeholder="e.g. Q3 report")
            u = fb.text_input("URL", placeholder="https://drive.google.com/…")
            if st.form_submit_button("Add link"):
                if core.clean_url(u):
                    core.add_project_link(pid, lbl, u, user["id"])
                    st.rerun()
                else:
                    st.error("Enter a valid http(s) URL.")


def _budget(proj, manages):
    pid = proj["id"]
    lines = core.list_budget_lines(pid)
    if not manages:
        if not lines:
            st.caption("No budget set.")
        else:
            st.dataframe(pd.DataFrame([{
                "Category": b["category"], "Detail": b["description"],
                "Amount": core.money(b["amount"])} for b in lines]),
                hide_index=True, width='stretch')
            st.caption(f"Total: {core.money(core.project_budget_total(pid))}")
        return
    rows = [{"Category": b["category"], "Detail": b["description"],
             "Amount": b["amount"]} for b in lines]
    base = pd.DataFrame(rows or [{"Category": core.CATEGORIES[0], "Detail": "",
                                  "Amount": 0.0}])
    edited = st.data_editor(base, num_rows="dynamic", width='stretch', key=f"bud_{pid}",
        column_config={
            "Category": st.column_config.SelectboxColumn(
                options=list(core.CATEGORIES), required=True),
            "Detail": st.column_config.TextColumn(width="large"),
            "Amount": st.column_config.NumberColumn(
                format=f"{core.CURRENCY}%.2f", min_value=0.0)})
    st.metric("Total budget", core.money(float(edited["Amount"].fillna(0).sum())))
    if st.button("Save budget", width='stretch'):
        core.set_budget_lines(pid, [{"category": r["Category"], "description": r["Detail"],
            "amount": r["Amount"]} for _, r in edited.iterrows()])
        st.success("Saved.")
        st.rerun()


def _about(user, proj, can_edit, manages):
    pid = proj["id"]
    is_founder = user["role"] == "founder"
    manageable = list(core.TRACKS) if is_founder else sorted(core.owned_tracks(user["id"]))
    name = st.text_input("Name", value=proj["name"], disabled=not can_edit)
    c1, c2 = st.columns(2)
    topts = manageable if (manages and manageable) else [proj["track"]]
    tidx = topts.index(proj["track"]) if proj["track"] in topts else 0
    track = c1.selectbox("Track", topts, index=tidx, disabled=not manages)
    status = c2.selectbox("Status", list(core.PROJECT_STATUSES),
        index=list(core.PROJECT_STATUSES).index(proj["status"]),
        format_func=lambda s: s.replace("_", " ").title(), disabled=not can_edit)
    desc = st.text_area("Description", value=proj["description"] or "", height=90,
                        disabled=not can_edit)
    reqs = st.text_area("Requirements", value=proj["requirements"] or "", height=100,
                        disabled=not can_edit)
    if can_edit and st.button("Save details", type="primary", width='stretch',
                              disabled=not name):
        core.update_project(pid, name, desc, reqs, status,
                            track if manages else proj["track"])
        st.success("Saved.")
        st.rerun()

    if manages:
        with st.expander("Archive project"):
            st.caption("Archiving hides the project but keeps everything (tasks, updates, "
                       "budget). You can restore it any time — nothing is deleted.")
            confirm = st.text_input("Type the project name to confirm", key=f"arch_{pid}")
            if st.button("Archive project", width='stretch',
                         disabled=(confirm != proj["name"])):
                core.archive_project(pid)
                st.session_state.pop("open_project", None)
                st.rerun()
