"""Projects. Everyone browses. Directors create/delete, set budgets and tracks.
Specialists edit any project; a track's leads edit projects in that track.
Budget stays director-only."""
import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="Projects · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Projects", "Portfolio")

role = user["role"]
is_director = role == "director"
is_specialist = role == "specialist"
my_tracks = core.lead_tracks(user["id"])          # tracks this user leads
coords = core.track_coordinators()                # {track: {name, user_id}}


def _fmt_status(s: str) -> str:
    return s.replace("_", " ").title()


def _can_edit(project) -> bool:
    return core.can_edit_project_role(role, project.get("track") in my_tracks)


def browse():
    projects = core.list_projects()
    if not projects:
        st.info("No projects yet.")
        return
    tracks_present = [t for t in core.TRACKS if any(p["track"] == t for p in projects)]
    flt = st.selectbox("Track", ["All tracks"] + tracks_present, key="browse_track")
    shown = projects if flt == "All tracks" else [p for p in projects if p["track"] == flt]
    for p in shown:
        with st.expander(f'{p["name"]}  ·  {p["track"] or "—"}  ·  '
                         f'{_fmt_status(p["status"])}'):
            coord = coords.get(p["track"], {}).get("name")
            leads = ", ".join(l["name"] for l in core.list_track_leads(p["track"])) \
                if p["track"] else ""
            st.markdown(
                f'<span class="meta">Track coordinator: {coord or "—"} · '
                f'Leads: {leads or "—"}</span>', unsafe_allow_html=True)
            if p["description"]:
                st.write(p["description"])
            if p["requirements"]:
                st.markdown("**Requirements**")
                st.write(p["requirements"])
            bl = core.list_budget_lines(p["id"])
            if bl:
                st.markdown("**Budget**")
                st.dataframe(pd.DataFrame([{
                    "Category": b["category"], "Detail": b["description"],
                    "Amount": core.money(b["amount"])} for b in bl]),
                    hide_index=True, width='stretch')
                st.caption(f'Total budget: {core.money(core.project_budget_total(p["id"]))}')
            recent = core.list_progress(project_id=p["id"], limit=3)
            if recent:
                st.markdown("**Latest progress**")
                for g in recent:
                    st.markdown(
                        f'{ui.status_pill(g["status"])} '
                        f'<span class="meta">{g["week_start"]} · '
                        f'{g["author_name"] or "—"}</span>', unsafe_allow_html=True)
                    if g["note"]:
                        st.caption(g["note"])


def editor():
    projects = core.list_projects()
    if is_director or is_specialist:
        pickable = projects
    else:
        pickable = [p for p in projects if p.get("track") in my_tracks]

    choices = {}
    if is_director:
        choices["➕ New project"] = None
    choices |= {f'{p["name"]} (#{p["id"]})': p["id"] for p in pickable}
    if not choices:
        st.info("Nothing to edit yet.")
        return

    pick = st.selectbox("Project", list(choices), key="proj_pick")
    pid = choices[pick]
    ex = core.get_project(pid) if pid else None
    can_edit = is_director or is_specialist or (ex and ex.get("track") in my_tracks)

    name = st.text_input("Name", value=ex["name"] if ex else "", disabled=not can_edit)
    c1, c2 = st.columns(2)
    # Track is a director-controlled property (it defines who can edit the project).
    track_idx = core.TRACKS.index(ex["track"]) if ex and ex.get("track") in core.TRACKS else 0
    track = c1.selectbox("Track", list(core.TRACKS), index=track_idx,
                         disabled=not is_director)
    status = c2.selectbox(
        "Status", list(core.PROJECT_STATUSES),
        index=list(core.PROJECT_STATUSES).index(ex["status"]) if ex else 1,
        format_func=_fmt_status, disabled=not can_edit)
    description = st.text_area("Description", value=ex["description"] if ex else "",
                              height=90, disabled=not can_edit)
    requirements = st.text_area("Requirements — what the project needs to succeed",
                               value=ex["requirements"] if ex else "", height=110,
                               disabled=not can_edit)

    if st.button("Save details", type="primary", width='stretch',
                 disabled=not (can_edit and name)):
        # Non-directors can't move a project between tracks.
        save_track = track if is_director else (ex["track"] if ex else track)
        if not pid:
            pid = core.create_project(name, description, requirements, status,
                                      save_track, user["id"])
        else:
            core.update_project(pid, name, description, requirements, status, save_track)
        st.success("Saved.")
        st.rerun()

    if is_director and ex:
        st.markdown("#### Budget breakdown")
        st.caption("Category, how it's spent, and amount. Directors only.")
        rows = [{"Category": b["category"], "Detail": b["description"],
                 "Amount": b["amount"]} for b in core.list_budget_lines(pid)]
        base = pd.DataFrame(rows or [{"Category": core.CATEGORIES[0],
                                      "Detail": "", "Amount": 0.0}])
        edited = st.data_editor(
            base, num_rows="dynamic", width='stretch', key=f"budget_ed_{pid}",
            column_config={
                "Category": st.column_config.SelectboxColumn(
                    options=list(core.CATEGORIES), required=True),
                "Detail": st.column_config.TextColumn(width="large"),
                "Amount": st.column_config.NumberColumn(
                    format=f"{core.CURRENCY}%.2f", min_value=0.0)})
        st.metric("Total budget", core.money(float(edited["Amount"].fillna(0).sum())))
        if st.button("Save budget", width='stretch'):
            core.set_budget_lines(pid, [
                {"category": r["Category"], "description": r["Detail"],
                 "amount": r["Amount"]} for _, r in edited.iterrows()])
            st.success("Budget saved.")
            st.rerun()

        with st.expander("Danger zone"):
            if st.button("Delete project", width='stretch'):
                core.delete_project(pid)
                st.warning("Project deleted.")
                st.rerun()


show_editor = is_director or is_specialist or bool(my_tracks)
if show_editor:
    t_browse, t_edit = st.tabs(["All projects", "Create / edit"])
    with t_browse:
        browse()
    with t_edit:
        editor()
else:
    browse()
    st.caption("Directors create projects and assign track leads (Team page). "
               "Leads can edit projects in their track.")
