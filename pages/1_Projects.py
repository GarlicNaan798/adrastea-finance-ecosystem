"""Projects. Everyone browses. Directors create/delete, set budgets, assign
leads. Specialists and a project's assigned leads can edit its details,
requirements, status and progress (not the budget)."""
import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="Projects · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Projects", "Portfolio")

role = user["role"]
is_director = role == "director"
my_leads = core.lead_project_ids(user["id"])


def _fmt_status(s: str) -> str:
    return s.replace("_", " ").title()


def _can_edit(project) -> bool:
    return core.can_edit_project_role(role, project["id"] in my_leads)


def browse():
    projects = core.list_projects()
    if not projects:
        st.info("No projects yet.")
        return
    for p in projects:
        leads = core.list_project_leads(p["id"])
        lead_names = ", ".join(l["name"] for l in leads) or "—"
        with st.expander(f'{p["name"]}  ·  {_fmt_status(p["status"])}  ·  '
                         f'{p["director_name"] or "—"}'):
            if p["description"]:
                st.write(p["description"])
            if p["requirements"]:
                st.markdown("**Requirements**")
                st.write(p["requirements"])
            st.markdown(f'<span class="meta">Leads: {lead_names}</span>',
                        unsafe_allow_html=True)
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
    # Directors & specialists may edit any project; a lead only their own.
    if is_director or role == "specialist":
        pickable = projects
    else:
        pickable = [p for p in projects if p["id"] in my_leads]

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
    can_edit = is_director or role == "specialist" or (pid in my_leads if pid else False)

    # --- Details (directors, specialists, that project's leads) --------------
    name = st.text_input("Name", value=ex["name"] if ex else "", disabled=not can_edit)
    status = st.selectbox(
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
        if not pid:
            pid = core.create_project(name, description, requirements, status, user["id"])
        else:
            core.update_project(pid, name, description, requirements, status)
        st.success("Saved.")
        st.rerun()

    # --- Budget (directors only) --------------------------------------------
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

    # --- Leads + delete (directors only) ------------------------------------
    if is_director and ex:
        st.markdown("#### Leads")
        st.caption("Assigned leads can edit this project's details, requirements, "
                   "status and progress.")
        people = {f'{u["name"]} · {u["email"]}': u["id"] for u in core.list_profiles()}
        current = {l["user_id"] for l in core.list_project_leads(pid)}
        default = [lbl for lbl, uid in people.items() if uid in current]
        chosen = st.multiselect("Project leads", list(people), default=default,
                                key=f"leads_{pid}")
        if st.button("Save leads", width='stretch'):
            chosen_ids = {people[l] for l in chosen}
            for uid in chosen_ids - current:
                core.assign_lead(pid, uid)
            for uid in current - chosen_ids:
                core.remove_lead(pid, uid)
            st.success("Leads updated.")
            st.rerun()

        with st.expander("Danger zone"):
            if st.button("Delete project", width='stretch'):
                core.delete_project(pid)
                st.warning("Project deleted.")
                st.rerun()


show_editor = is_director or role == "specialist" or bool(my_leads)
if show_editor:
    t_browse, t_edit = st.tabs(["All projects", "Create / edit"])
    with t_browse:
        browse()
    with t_edit:
        editor()
else:
    browse()
    st.caption("Directors create projects and assign leads. Ask a director to be "
               "made a lead or specialist to edit projects.")
