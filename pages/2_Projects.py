"""Funded projects: budget vs. actual spending per category."""
import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="Projects · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Projects", "Portfolio")

# Directors see their own projects; finance/admin see all.
mine = user["role"] == "director"
projects = core.list_projects(director_id=user["id"] if mine else None)

if not projects:
    st.info("No funded projects yet. Projects are created when a proposal is approved.")
    st.stop()

names = {f'{p["name"]} (#{p["id"]})': p["id"] for p in projects}
pick = st.selectbox("Project", list(names))
pid = names[pick]
proj = core.get_project(pid)

st.subheader(proj["name"])
if proj["description"]:
    st.write(proj["description"])

bva = core.budget_vs_actual(pid)
budget = sum(r["budget"] for r in bva)
spent = sum(r["spent"] for r in bva)
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    c1.metric("Approved budget", core.money(budget))
    c2.metric("Spent", core.money(spent))
    c3.metric("Remaining", core.money(budget - spent),
              delta=None if budget else "no approved budget")

if bva:
    df = pd.DataFrame(bva)
    st.markdown("#### Budget vs. actual by category")
    st.dataframe(
        df.assign(
            Budget=df["budget"].map(core.money),
            Spent=df["spent"].map(core.money),
            Remaining=df["remaining"].map(core.money),
        )[["category", "Budget", "Spent", "Remaining"]].rename(
            columns={"category": "Category"}),
        hide_index=True, use_container_width=True)
    over = df[df["remaining"] < 0]
    if not over.empty:
        st.error("Over budget in: " + ", ".join(over["category"]))
    chart = df.set_index("category")[["budget", "spent"]].rename(
        columns={"budget": "Budget", "spent": "Spent"})
    st.bar_chart(chart, color=[ui.STONE, ui.CLAY])

st.markdown("#### Transactions")
txns = core.list_transactions(project_id=pid)
if txns:
    st.dataframe(pd.DataFrame([{
        "Date": t["txn_date"], "Type": t["type"], "Category": t["category"],
        "Description": t["description"], "Amount": core.money(t["amount"]),
    } for t in txns]), hide_index=True, use_container_width=True)
else:
    st.caption("No transactions recorded against this project yet. "
               "Record them on the **Finance** page.")
