"""Org-wide finance: record transactions and see spending dashboards."""
from datetime import date

import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="Finance · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Finance & budget", "Treasury")

is_finance = user["role"] in ("finance", "admin")

# --- Dashboard (finance/admin) ----------------------------------------------
if is_finance:
    t = core.org_totals()
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Income", core.money(t["income"]))
        c2.metric("Spent", core.money(t["expense"]))
        c3.metric("Net position", core.money(t["net"]))
        c4.metric("Approved funding", core.money(t["approved_budget"]))

    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            st.subheader("Spending by category")
            cats = core.spend_by_category()
            if any(r["spent"] for r in cats):
                df = pd.DataFrame([{"Category": r["category"], "Spent": r["spent"]}
                                   for r in cats if r["spent"]]).set_index("Category")
                st.bar_chart(df, color=ui.CLAY)
            else:
                st.caption("No expenses yet.")
    with col_b:
        with st.container(border=True):
            st.subheader("Spending by project")
            projs = core.spend_by_project()
            if any(r["spent"] for r in projs):
                df = pd.DataFrame([{"Project": r["name"], "Spent": r["spent"]}
                                   for r in projs if r["spent"]]).set_index("Project")
                st.bar_chart(df, color=ui.CLAY)
            else:
                st.caption("No project spending yet.")
    st.divider()

# --- Record a transaction ---------------------------------------------------
st.markdown("#### Record a transaction")

# Directors may only log expenses against their own projects.
if is_finance:
    projects = core.list_projects()
else:
    projects = core.list_projects(director_id=user["id"])

proj_options = ({"— Organization-general —": None} if is_finance else {}) | {
    f'{p["name"]} (#{p["id"]})': p["id"] for p in projects}

if not proj_options:
    st.info("You have no projects to record spending against yet.")
else:
    with st.form("txn", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        d = col1.date_input("Date", value=date.today())
        ttype = col2.selectbox("Type", ["expense", "income"] if is_finance else ["expense"])
        proj_label = col3.selectbox("Project", list(proj_options))
        col4, col5 = st.columns(2)
        category = col4.selectbox("Category", list(core.CATEGORIES))
        amount = col5.number_input("Amount", min_value=0.0, step=50.0,
                                   format="%.2f")
        description = st.text_input("Description")
        if st.form_submit_button("Record", type="primary", use_container_width=True):
            if amount <= 0:
                st.error("Amount must be greater than zero.")
            else:
                core.create_transaction(
                    d.isoformat(), ttype, proj_options[proj_label], category,
                    description, amount, user["id"])
                st.success("Transaction recorded.")
                st.rerun()

# --- Ledger -----------------------------------------------------------------
st.markdown("#### Ledger")
txns = (core.list_transactions() if is_finance
        else [t for p in projects
              for t in core.list_transactions(project_id=p["id"])])
if txns:
    st.dataframe(pd.DataFrame([{
        "Date": t["txn_date"], "Type": t["type"],
        "Project": t["project_name"] or "— org-general —",
        "Category": t["category"], "Description": t["description"],
        "Amount": core.money(t["amount"]),
    } for t in txns]), hide_index=True, use_container_width=True)
else:
    st.caption("No transactions recorded yet.")
