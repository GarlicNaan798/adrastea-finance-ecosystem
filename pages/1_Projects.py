"""Projects. Everyone browses. A founder or a track's director creates/deletes,
sets budgets and the track. Leads (and directors) edit details on their track's
projects. Budget/create/delete stay with founders and the track director."""
import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="Projects · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Projects", "Portfolio")

uid, role = user["id"], user["role"]
is_founder = role == "founder"
owned = core.owned_tracks(uid)     # tracks this user directs
led = core.lead_tracks(uid)        # tracks where this user is a team lead
directors = core.track_directors()  # {track: {name, user_id}}


def _fmt_status(s: str) -> str:
    return s.replace("_", " ").title()


def manages(track) -> bool:        # create/delete/budget/team
    return is_founder or track in owned


def can_edit(track) -> bool:       # edit details/status
    return is_founder or track in owned or track in led


def manageable_tracks():
    return list(core.TRACKS) if is_founder else sorted(owned)


def browse():
    projects = core.list_projects()
    if not projects:
        st.info("No projects yet.")
        return
    present = [t for t in core.TRACKS if any(p["track"] == t for p in projects)]
    flt = st.selectbox("Track", ["All tracks"] + present, key="browse_track")
    shown = projects if flt == "All tracks" else [p for p in projects if p["track"] == flt]
    for p in shown:
        with st.expander(f'{p["name"]}  ·  {p["track"] or "—"}  ·  {_fmt_status(p["status"])}'):
            d = directors.get(p["track"], {}).get("name") or "—"
            leads = ", ".join(m["name"] for m in core.list_track_members(p["track"])
                              if m["is_lead"]) or "—"
            st.markdown(f'<span class="meta">Director: {d} · Leads: {leads}</span>',
                        unsafe_allow_html=True)
            if p["description"]:
                st.write(p["description"])
            if p["requirements"]:
                st.markdown("**Requirements**")
                st.write(p["requirements"])
            for l in core.list_project_links(p["id"]):
                st.markdown(f'- [{l["label"] or l["url"]}]({l["url"]})')
            bl = core.list_budget_lines(p["id"])
            if bl:
                st.markdown("**Budget**")
                st.dataframe(pd.DataFrame([{
                    "Category": b["category"], "Detail": b["description"],
                    "Amount": core.money(b["amount"])} for b in bl]),
                    hide_index=True, width='stretch')
                st.caption(f'Total: {core.money(core.project_budget_total(p["id"]))}')


def editor():
    projects = core.list_projects()
    editable = [p for p in projects if can_edit(p["track"])]
    choices = {}
    if manageable_tracks():
        choices["➕ New project"] = None
    choices |= {f'{p["name"]} (#{p["id"]})': p["id"] for p in editable}
    if not choices:
        st.info("Nothing to edit yet.")
        return

    pick = st.selectbox("Project", list(choices), key="proj_pick")
    pid = choices[pick]
    ex = core.get_project(pid) if pid else None
    ce = True if not ex else can_edit(ex["track"])
    cm_track = ex["track"] if ex else (manageable_tracks() or list(core.TRACKS))[0]
    can_manage = manages(cm_track)

    name = st.text_input("Name", value=ex["name"] if ex else "", disabled=not ce)
    c1, c2 = st.columns(2)
    # Track: managers pick from tracks they manage; leads can't move a project.
    topts = manageable_tracks() if can_manage else [ex["track"]] if ex else manageable_tracks()
    tidx = topts.index(ex["track"]) if ex and ex["track"] in topts else 0
    track = c1.selectbox("Track", topts, index=tidx, disabled=not can_manage)
    status = c2.selectbox("Status", list(core.PROJECT_STATUSES),
        index=list(core.PROJECT_STATUSES).index(ex["status"]) if ex else 1,
        format_func=_fmt_status, disabled=not ce)
    description = st.text_area("Description", value=ex["description"] if ex else "",
                              height=90, disabled=not ce)
    requirements = st.text_area("Requirements", value=ex["requirements"] if ex else "",
                               height=100, disabled=not ce)

    if st.button("Save details", type="primary", width='stretch',
                 disabled=not (ce and name)):
        save_track = track if can_manage else (ex["track"] if ex else track)
        if not pid:
            pid = core.create_project(name, description, requirements, status,
                                      save_track, uid)
        else:
            core.update_project(pid, name, description, requirements, status, save_track)
        st.success("Saved.")
        st.rerun()

    # Documents (any editor)
    if ex and ce:
        st.markdown("#### Documents & links")
        st.caption("Attach Google Drive / Docs links (or any URL).")
        for l in core.list_project_links(pid):
            a, b = st.columns([5, 1])
            a.markdown(f'[{l["label"] or l["url"]}]({l["url"]})', unsafe_allow_html=True)
            if b.button("Remove", key=f"rml_{l['id']}", width='stretch'):
                core.delete_project_link(l["id"]); st.rerun()
        with st.form(f"addlink_{pid}", clear_on_submit=True):
            fa, fb = st.columns([2, 3])
            lbl = fa.text_input("Label", placeholder="e.g. Q3 report")
            u = fb.text_input("URL", placeholder="https://drive.google.com/…")
            if st.form_submit_button("Add link"):
                if core.clean_url(u):
                    core.add_project_link(pid, lbl, u, uid); st.success("Added."); st.rerun()
                else:
                    st.error("Enter a valid http(s) URL.")

    # Budget + delete (managers only)
    if ex and can_manage:
        st.markdown("#### Budget breakdown")
        rows = [{"Category": b["category"], "Detail": b["description"],
                 "Amount": b["amount"]} for b in core.list_budget_lines(pid)]
        base = pd.DataFrame(rows or [{"Category": core.CATEGORIES[0], "Detail": "",
                                      "Amount": 0.0}])
        edited = st.data_editor(base, num_rows="dynamic", width='stretch',
            key=f"budget_ed_{pid}", column_config={
                "Category": st.column_config.SelectboxColumn(
                    options=list(core.CATEGORIES), required=True),
                "Detail": st.column_config.TextColumn(width="large"),
                "Amount": st.column_config.NumberColumn(
                    format=f"{core.CURRENCY}%.2f", min_value=0.0)})
        st.metric("Total budget", core.money(float(edited["Amount"].fillna(0).sum())))
        if st.button("Save budget", width='stretch'):
            core.set_budget_lines(pid, [{"category": r["Category"],
                "description": r["Detail"], "amount": r["Amount"]}
                for _, r in edited.iterrows()])
            st.success("Budget saved."); st.rerun()
        with st.expander("Archive project"):
            st.caption("Archiving hides the project but keeps everything (tasks, "
                       "updates, budget). You can restore it any time. Nothing is "
                       "permanently deleted.")
            confirm = st.text_input("Type the project name to confirm",
                                    key=f"arch_{pid}")
            if st.button("Archive project", width='stretch',
                         disabled=(confirm != ex["name"])):
                core.archive_project(pid)
                st.warning("Archived.")
                st.rerun()

    arch = [a for a in core.list_archived_projects() if manages(a["track"])]
    if arch:
        st.markdown("#### Archived (restore)")
        for a in arch:
            r1, r2 = st.columns([4, 1])
            r1.write(f'{a["name"]} · {a["track"]}')
            if r2.button("Restore", key=f"rest_{a['id']}", width='stretch'):
                core.restore_project(a["id"])
                st.success("Restored.")
                st.rerun()


if is_founder or owned or led:
    tb, te = st.tabs(["All projects", "Create / edit"])
    with tb:
        browse()
    with te:
        editor()
else:
    browse()
    st.caption("A founder or track director creates projects and builds teams. "
               "Ask to be added to a track's team to contribute.")
