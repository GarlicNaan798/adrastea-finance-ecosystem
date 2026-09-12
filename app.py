"""Adrastea — overview / landing. Run with:  streamlit run app.py"""
import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()

ui.page_header("Adrastea", "Research funding & finance")
st.caption(f"Welcome back, {user['name'].split()[0]}.")

# --- Org snapshot (everyone sees it) ----------------------------------------
t = core.org_totals()
with st.container(border=True):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Income", core.money(t["income"]))
    c2.metric("Spent", core.money(t["expense"]))
    c3.metric("Net position", core.money(t["net"]))
    c4.metric("Approved funding", core.money(t["approved_budget"]))

pending = len(core.list_proposals(status="submitted"))
if pending and user["role"] in ("finance", "admin"):
    st.warning(f"{pending} proposal(s) awaiting your review — see **Proposals**.")

st.write("")
col_a, col_b = st.columns(2)

with col_a:
    with st.container(border=True):
        st.subheader("Proposals")
        mine = user["role"] == "director"
        props = core.list_proposals(director_id=user["id"] if mine else None)
        if props:
            df = pd.DataFrame([{
                "Title": p["title"], "Director": p["director_name"],
                "Status": p["status"], "Requested": core.money(p["requested_amount"]),
            } for p in props])
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.info("No proposals yet. Head to **Proposals** to create one.")

with col_b:
    with st.container(border=True):
        st.subheader("Spending by project")
        rows = core.spend_by_project()
        if any(r["spent"] for r in rows):
            df = pd.DataFrame([{"Project": r["name"], "Spent": r["spent"]}
                               for r in rows if r["spent"]]).set_index("Project")
            st.bar_chart(df, color=ui.CLAY)
        else:
            st.info("No spending recorded yet.")
