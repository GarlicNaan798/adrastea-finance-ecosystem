"""Projects: everyone browses; directors set projects, requirements, budgets."""
import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="Projects · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Projects", "Portfolio")

is_director = user["role"] == "director"


def _fmt_status(s: str) -> str:
    return s.replace("_", " ").title()


def browse():
    projects = core.list_projects()
    if not projects:
        st.info("No projects yet.")
        return
    for p in projects:
        with st.expander(f'{p["name"]}  ·  {_fmt_status(p["status"])}  ·  '
                         f'{p["director_name"] or "—"}'):
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
                        f'<span style="color:#8a857c">{g["week_start"]} · '
                        f'{g["author_name"] or "—"}</span>', unsafe_allow_html=True)
                    if g["note"]:
                        st.caption(g["note"])


def editor():
    ui.require_role(user, "director")
    mine = core.list_projects()
    choices = {"➕ New project": None} | {f'{p["name"]} (#{p["id"]})': p["id"]
                                          for p in mine}
    pick = st.selectbox("Project", list(choices), key="proj_pick")
    pid = choices[pick]
    ex = core.get_project(pid) if pid else None

    name = st.text_input("Name", value=ex["name"] if ex else "")
    c1, c2 = st.columns(2)
    status = c1.selectbox("Status", list(core.PROJECT_STATUSES),
                          index=list(core.PROJECT_STATUSES).index(ex["status"]) if ex else 1,
                          format_func=_fmt_status)
    description = st.text_area("Description", value=ex["description"] if ex else "",
                              height=90)
    requirements = st.text_area("Requirements — what the project needs to succeed",
                               value=ex["requirements"] if ex else "", height=110)

    st.markdown("#### Budget breakdown")
    st.caption("Category, how it's spent, and amount. Directors only.")
    existing = ([{"Category": b["category"], "Detail": b["description"],
                  "Amount": b["amount"]} for b in core.list_budget_lines(pid)]
                if ex else [])
    base = pd.DataFrame(existing or [{"Category": core.CATEGORIES[0],
                                      "Detail": "", "Amount": 0.0}])
    edited = st.data_editor(
        base, num_rows="dynamic", width='stretch', key="budget_ed",
        column_config={
            "Category": st.column_config.SelectboxColumn(
                options=list(core.CATEGORIES), required=True),
            "Detail": st.column_config.TextColumn(width="large"),
            "Amount": st.column_config.NumberColumn(
                format=f"{core.CURRENCY}%.2f", min_value=0.0)})
    st.metric("Total budget", core.money(float(edited["Amount"].fillna(0).sum())))

    b1, b2 = st.columns(2)
    if b1.button("Save project", type="primary", width='stretch',
                 disabled=not name):
        lines = [{"category": r["Category"], "description": r["Detail"],
                  "amount": r["Amount"]} for _, r in edited.iterrows()]
        if not pid:
            pid = core.create_project(name, description, requirements, status,
                                      user["id"])
        else:
            core.update_project(pid, name, description, requirements, status)
        core.set_budget_lines(pid, lines)
        st.success("Saved.")
        st.rerun()
    if ex and b2.button("Delete project", width='stretch'):
        core.delete_project(pid)
        st.warning("Project deleted.")
        st.rerun()


if is_director:
    t_browse, t_edit = st.tabs(["All projects", "Create / edit"])
    with t_browse:
        browse()
    with t_edit:
        editor()
else:
    browse()
    st.caption("Only directors can create or edit projects.")
