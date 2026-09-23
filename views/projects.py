"""Projects: a list grouped by track, and a per-project workspace with tabs
(Updates / Tasks / Deadlines / Docs / Budget / About) — the ManageBac 'class' model.
Everything about a project lives in one place instead of scattered global pages."""
from datetime import date
from html import escape

import altair as alt
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
        with st.expander("New project", icon=":material/add:"):
            _new_project(user, manageable)

    projects = core.list_projects()
    if not projects:
        ui.empty("No projects yet."
                 + (" Create one above." if manageable else " Ask a director to add one."))
    else:
        latest = {r["project_id"]: r for r in core.latest_progress_by_project()}
        present = [t for t in core.TRACKS if any(p["track"] == t for p in projects)]
        for track in present:
            in_track = [p for p in projects if p["track"] == track]
            ui.section(track, len(in_track),
                       f'Director: {directors.get(track, {}).get("name") or "—"}')
            for p in in_track:
                lp = latest.get(p["id"])
                if ui.row(f"open_{p['id']}", p["name"],
                          p["status"].replace("_", " ").title()
                          + (f' · last update {ui.when(lp["created_at"])}' if lp else ""),
                          aside=ui.status_pill(lp["status"]) if lp else "No updates"):
                    st.session_state.open_project = p["id"]
                    st.rerun()
            st.write("")

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
    pid, track = proj["id"], proj["track"]
    owned, led = core.owned_tracks(uid), core.lead_tracks(uid)
    member_of = core.member_tracks(uid)
    manages = is_founder or track in owned          # budget, archive, move track
    can_edit = manages or track in led              # details, deadlines, docs, tasks
    can_post = manages or track in member_of        # stream updates

    if st.button("All projects", type="tertiary", icon=":material/arrow_back:"):
        st.session_state.pop("open_project", None)
        st.rerun()
    directors = core.track_directors()
    leads = ", ".join(m["name"] for m in core.list_track_members(track)
                      if m["is_lead"]) or "—"
    ui.page_header(proj["name"], track,
                   f'{proj["status"].replace("_", " ").title()} · '
                   f'Director: {directors.get(track, {}).get("name") or "—"} · Leads: {leads}')

    latest = next(iter(core.list_progress(project_id=pid, limit=1)), None)
    open_tasks = [t for t in core.list_tasks(project_id=pid) if t["status"] != "done"]
    nxt = min((m for m in core.list_milestones(pid) if not m["done"] and m["due_date"]),
              key=lambda m: m["due_date"], default=None)
    health = latest["status"] if latest else None
    ui.readout([
        ("Health", core.PROGRESS_LABELS.get(health, "No updates"),
         health in ("at_risk", "blocked")),
        ("Open tasks", len(open_tasks), False),
        ("Next deadline", ui.fmt_date(nxt["due_date"]) if nxt else "—",
         bool(nxt) and nxt["due_date"][:10] < date.today().isoformat()),
        ("Budget", f"{core.CURRENCY}{core.project_budget_total(pid):,.0f}", False)])

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
    feed = core.list_progress(project_id=pid, limit=200)
    log, side = st.columns([1.75, 1], gap="large")
    with side:
        ui.section("Post an update")
        if can_post:
            with st.form("post", clear_on_submit=True, border=False):
                title = st.text_input("Update", placeholder="e.g. Sensor array wired up")
                status = st.selectbox("Status", list(core.PROGRESS_STATUSES),
                                      format_func=lambda s: core.PROGRESS_LABELS[s])
                note = st.text_area("Details", height=110)
                if st.form_submit_button("Post update", type="primary", width='stretch'):
                    if not title.strip():
                        st.error("Add a short title.")
                    else:
                        core.add_progress(pid, user["id"], title, status, note.strip())
                        st.rerun()
        else:
            ui.empty("Ask to join this track's team to post updates.")
    with log:
        ui.section("Update history", len(feed))
        if not feed:
            ui.empty("No updates yet.")
        for g in feed:
            with st.container(key=f"log_{g['id']}", gap=None):
                st.markdown(ui.log_entry(
                    g["created_at"], ui.status_pill(g["status"]), g["title"] or "(untitled)",
                    g["note"] or "", g["author_name"] or "—"), unsafe_allow_html=True)
                ui.comment_thread("update", g["id"], user, can_post)


def _task_links(task, can_edit, uid):
    links = core.list_task_links(task["id"])
    with st.expander(f"Attachments ({len(links)})"):
        for l in links:
            a, b = st.columns([5, 1])
            a.markdown(ui.link(l["label"], l["url"]), unsafe_allow_html=True)
            if can_edit and b.button("Remove", key=f"tlrm_{l['id']}", type="tertiary"):
                core.delete_task_link(l["id"])
                st.rerun()
        if can_edit:
            with st.form(f"tl_{task['id']}", clear_on_submit=True, border=False):
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
        with st.expander("New task", icon=":material/add:"):
            with st.form("addtask", clear_on_submit=True, border=False):
                title = st.text_input("Task")
                desc = st.text_area("Details", height=68)
                a, b = st.columns(2)
                who = a.selectbox("Assign to", list(assignees))
                due = b.date_input("Due (optional)", value=None)
                if st.form_submit_button("Create task", type="primary"):
                    if not title.strip():
                        st.error("Add a task title.")
                    else:
                        core.create_task(pid, title, desc, assignees[who],
                                         due.isoformat() if isinstance(due, date) else None,
                                         uid)
                        st.rerun()
            if len(assignees) == 1:
                st.caption("No team on this track yet — add members on the Team page.")

    tlist = core.list_tasks(project_id=pid)
    if tlist and _HAS_BOARD and can_assign:
        ui.section("Board", note="Drag cards between columns")
        by_id = {t["id"]: t for t in tlist}
        cols = [{"header": h, "items": [f'#{t["id"]} {t["title"]}' for t in tlist
                                        if t["status"] == s]} for h, s in _BOARD.items()]
        try:
            res = sort_items(cols, multi_containers=True, direction="horizontal",
                             custom_style=ui.BOARD_CSS, key=f"board_{pid}")
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
        st.write("")

    for label, group in (("Open", [t for t in tlist if t["status"] != "done"]),
                         ("Done", [t for t in tlist if t["status"] == "done"])):
        if label == "Done" and not group:
            continue
        ui.section(label, len(group))
        if not group:
            ui.empty("No open tasks.")
        for t in group:
            _task_item(user, t, can_assign)
        st.write("")


def _task_item(user, t, can_assign):
    uid = user["id"]
    can_e = can_assign or t["assignee_id"] == uid   # its assignee, or a manager/lead
    with st.container(key=f"task_{t['id']}", gap=None):
        c1, c0, c2, c3 = st.columns([4, 1, 1.4, .8], vertical_alignment="center")
        c1.markdown(
            f'<div class="adr-item"><div class="t">{escape(t["title"])}</div>'
            f'<div class="s">{escape(t["assignee_name"] or "Unassigned")}</div></div>',
            unsafe_allow_html=True)
        c0.markdown(f'<div class="adr-item-due">{ui.due(t["due_date"], t["status"] == "done")}'
                    f'</div>', unsafe_allow_html=True)
        ns = c2.selectbox("Status", list(core.TASK_STATUSES),
                          index=list(core.TASK_STATUSES).index(t["status"]),
                          format_func=lambda s: core.TASK_LABELS[s],
                          key=f"tst_{t['id']}", label_visibility="collapsed",
                          disabled=not can_e)
        if can_e and ns != t["status"]:
            core.set_task_status(t["id"], ns)
            st.rerun()
        if can_assign and c3.button("Archive", key=f"arc_{t['id']}", type="tertiary"):
            core.archive_task(t["id"])
            st.rerun()
        d1, d2 = st.columns(2)
        with d1:
            _task_links(t, can_e, uid)
        with d2:
            ui.comment_thread("task", t["id"], user, can_e)


def _deadlines(proj, can_edit):
    pid = proj["id"]
    ms = sorted(core.list_milestones(pid), key=lambda m: (m["done"], m["due_date"] or "9"))
    ui.section("Milestones", len(ms), f'{sum(m["done"] for m in ms)} of {len(ms)} complete'
               if ms else "")
    if not ms:
        ui.empty("No milestones yet.")
    for m in ms:
        with st.container(key=f"msrow_{m['id']}", gap=None):
            c1, c2, c3 = st.columns([5, 1.2, .8], vertical_alignment="center")
            label = f'~~{m["title"]}~~' if m["done"] else m["title"]
            done = c1.checkbox(label, value=m["done"], key=f"ms_{m['id']}",
                               disabled=not can_edit)
            if can_edit and done != m["done"]:
                core.toggle_milestone(m["id"], done)
                st.rerun()
            c2.markdown(f'<div class="adr-item-due">{ui.due(m["due_date"], m["done"])}</div>',
                        unsafe_allow_html=True)
            if can_edit and c3.button("Remove", key=f"msrm_{m['id']}", type="tertiary"):
                core.remove_milestone(m["id"])
                st.rerun()
    if can_edit:
        st.write("")
        with st.form(f"addms_{pid}", clear_on_submit=True, border=False):
            g1, g2, g3 = st.columns([3, 1.6, 1], vertical_alignment="bottom")
            mt = g1.text_input("New milestone")
            md = g2.date_input("Due (optional)", value=None)
            if g3.form_submit_button("Add", width='stretch'):
                if mt.strip():
                    core.add_milestone(pid, mt,
                                       md.isoformat() if isinstance(md, date) else None)
                    st.rerun()
                else:
                    st.error("Add a milestone title.")


def _docs(user, proj, can_edit):
    pid = proj["id"]
    links = core.list_project_links(pid)
    ui.section("Documents", len(links), "Google Drive / Docs links, or any URL")
    if not links:
        ui.empty("No documents attached.")
    for l in links:
        with st.container(key=f"doc_{l['id']}", gap=None):
            a, b = st.columns([6, .8], vertical_alignment="center")
            a.markdown(ui.doc_row(l["label"], l["url"]), unsafe_allow_html=True)
            if can_edit and b.button("Remove", key=f"rml_{l['id']}", type="tertiary"):
                core.delete_project_link(l["id"])
                st.rerun()
    if can_edit:
        st.write("")
        with st.form(f"addlink_{pid}", clear_on_submit=True, border=False):
            fa, fb, fc = st.columns([2, 3, 1], vertical_alignment="bottom")
            lbl = fa.text_input("Label", placeholder="e.g. Q3 report")
            u = fb.text_input("URL", placeholder="https://drive.google.com/…")
            if fc.form_submit_button("Add link", width='stretch'):
                if core.clean_url(u):
                    core.add_project_link(pid, lbl, u, user["id"])
                    st.rerun()
                else:
                    st.error("Enter a valid http(s) URL.")


def _budget_chart(df):
    """Spend by category — clay bars, no gridlines, like a printed report figure."""
    by = (df.assign(Amount=df["Amount"].fillna(0)).groupby("Category", as_index=False)
          ["Amount"].sum().query("Amount > 0"))
    if by.empty:
        return
    base = alt.Chart(by).encode(
        y=alt.Y("Category:N", sort="-x", title=None,
                axis=alt.Axis(labelLimit=220, ticks=False, domain=False, labelPadding=8)),
        x=alt.X("Amount:Q", title=None, axis=None,  # headroom so value labels fit
                scale=alt.Scale(domain=[0, float(by["Amount"].max()) * 1.35])))
    bars = base.mark_bar(color=ui.CLAY, height=14)
    dark = getattr(st.context.theme, "type", None) == "dark"
    text = base.mark_text(align="left", dx=6, fontSize=12,
                          color="#ECE7DD" if dark else "#23211C").encode(
        text=alt.Text("Amount:Q", format=",.0f"))
    st.altair_chart((bars + text).properties(height=34 * len(by) + 10)
                    .configure_view(stroke=None), width='stretch')


def _budget(proj, manages):
    pid = proj["id"]
    lines = core.list_budget_lines(pid)
    rows = [{"Category": b["category"], "Detail": b["description"],
             "Amount": b["amount"]} for b in lines]
    if not manages:
        ui.section("Spend by category")
        if not lines:
            ui.empty("No budget set.")
            return
        _budget_chart(pd.DataFrame(rows))
        ui.section("Line items", len(lines), f"Total {core.money(core.project_budget_total(pid))}")
        st.dataframe(pd.DataFrame([{**r, "Amount": core.money(r["Amount"])} for r in rows]),
                     hide_index=True, width='stretch')
        return
    base = pd.DataFrame(rows or [{"Category": core.CATEGORIES[0], "Detail": "",
                                  "Amount": 0.0}])
    chart, edit = st.columns([1, 1.5], gap="large")
    with edit:
        ui.section("Line items", note="Edit cells, add or delete rows, then save")
        edited = st.data_editor(base, num_rows="dynamic", width='stretch', key=f"bud_{pid}",
            column_config={
                "Category": st.column_config.SelectboxColumn(
                    options=list(core.CATEGORIES), required=True),
                "Detail": st.column_config.TextColumn(width="large"),
                "Amount": st.column_config.NumberColumn(
                    format=f"{core.CURRENCY}%.2f", min_value=0.0)})
        if st.button("Save budget", type="primary"):
            core.set_budget_lines(pid, [{"category": r["Category"],
                "description": r["Detail"], "amount": r["Amount"]}
                for _, r in edited.iterrows()])
            st.success("Saved.")
            st.rerun()
    with chart:
        ui.section("Spend by category",
                   note=f'Total {core.money(float(edited["Amount"].fillna(0).sum()))}')
        _budget_chart(edited)


def _about(user, proj, can_edit, manages):
    pid = proj["id"]
    is_founder = user["role"] == "founder"
    manageable = list(core.TRACKS) if is_founder else sorted(core.owned_tracks(user["id"]))
    main, side = st.columns([1.75, 1], gap="large")
    with main:
        ui.section("Project details")
        name = st.text_input("Name", value=proj["name"], disabled=not can_edit)
        c1, c2 = st.columns(2)
        topts = manageable if (manages and manageable) else [proj["track"]]
        tidx = topts.index(proj["track"]) if proj["track"] in topts else 0
        track = c1.selectbox("Track", topts, index=tidx, disabled=not manages)
        status = c2.selectbox("Status", list(core.PROJECT_STATUSES),
            index=list(core.PROJECT_STATUSES).index(proj["status"]),
            format_func=lambda s: s.replace("_", " ").title(), disabled=not can_edit)
        desc = st.text_area("Description", value=proj["description"] or "", height=110,
                            disabled=not can_edit)
        reqs = st.text_area("Requirements", value=proj["requirements"] or "", height=130,
                            disabled=not can_edit)
        if can_edit and st.button("Save details", type="primary", disabled=not name):
            core.update_project(pid, name, desc, reqs, status,
                                track if manages else proj["track"])
            st.success("Saved.")
            st.rerun()
    with side:
        ui.section("Access")
        st.caption("Directors and founders manage budget, track and archiving. Leads edit "
                   "details, deadlines, docs and tasks. Track members post updates.")
        if manages:
            st.write("")
            ui.section("Archive")
            st.caption("Archiving hides the project but keeps everything (tasks, updates, "
                       "budget). You can restore it any time — nothing is deleted.")
            confirm = st.text_input("Type the project name to confirm", key=f"arch_{pid}")
            if st.button("Archive project", disabled=(confirm != proj["name"])):
                core.archive_project(pid)
                st.session_state.pop("open_project", None)
                st.rerun()
