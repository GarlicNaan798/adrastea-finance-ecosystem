"""Submit funding proposals with a budget breakdown; finance/admin review them."""
import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="Proposals · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Proposals", "Funding")

can_review = user["role"] in ("finance", "admin")
can_author = user["role"] in ("director", "admin")

tabs = st.tabs(
    (["Write a proposal"] if can_author else [])
    + ["All proposals"]
    + (["Review queue"] if can_review else [])
)
idx = 0

# --- Author tab -------------------------------------------------------------
if can_author:
    with tabs[idx]:
        drafts = [p for p in core.list_proposals(director_id=user["id"])
                  if p["status"] == "draft"]
        choices = {"New proposal": None} | {
            f'{p["title"]} (draft #{p["id"]})': p["id"] for p in drafts}
        pick = st.selectbox("Proposal", list(choices), key="prop_pick")
        pid = choices[pick]
        existing = core.get_proposal(pid) if pid else None

        title = st.text_input("Title", value=existing["title"] if existing else "")
        col1, col2 = st.columns(2)
        fy = col1.text_input("Fiscal year",
                             value=existing["fiscal_year"] if existing else "2026")
        summary = st.text_area(
            "Summary — what the project does and why it needs funding",
            value=existing["summary"] if existing else "", height=120)

        st.markdown("#### Budget breakdown")
        st.caption("Where the money goes (category) and how it will be spent "
                   "(description). Requested total is the sum of these lines.")
        if existing:
            lines = [{"Category": ln["category"], "Description": ln["description"],
                      "Amount": ln["amount"]}
                     for ln in core.list_budget_lines(pid)]
        else:
            lines = []
        base = pd.DataFrame(lines or [{"Category": core.CATEGORIES[0],
                                       "Description": "", "Amount": 0.0}])
        edited = st.data_editor(
            base, num_rows="dynamic", use_container_width=True, key="budget_ed",
            column_config={
                "Category": st.column_config.SelectboxColumn(
                    options=list(core.CATEGORIES), required=True),
                "Description": st.column_config.TextColumn(width="large"),
                "Amount": st.column_config.NumberColumn(
                    format=f"{core.CURRENCY}%.2f", min_value=0.0),
            })
        total = float(edited["Amount"].fillna(0).sum())
        st.metric("Requested total", core.money(total))

        b1, b2 = st.columns(2)
        if b1.button("Save draft", use_container_width=True, disabled=not title):
            if not pid:
                pid = core.create_proposal(title, user["id"], summary, fy)
            else:
                core.update_proposal(pid, title, summary, fy)
            core.set_budget_lines(pid, [
                {"category": r["Category"], "description": r["Description"],
                 "amount": r["Amount"]} for _, r in edited.iterrows()])
            st.success("Saved draft.")
            st.rerun()
        if b2.button("Submit for review", use_container_width=True,
                     disabled=not pid, type="primary"):
            core.submit_proposal(pid)
            st.success("Submitted for review.")
            st.rerun()
    idx += 1

# --- All proposals tab ------------------------------------------------------
with tabs[idx]:
    mine_only = user["role"] == "director"
    props = core.list_proposals(director_id=user["id"] if mine_only else None)
    if not props:
        st.info("No proposals yet.")
    for p in props:
        with st.expander(
                f'{p["title"]} — {p["status"].upper()} · '
                f'{core.money(p["requested_amount"])} · {p["director_name"]}'):
            st.write(p["summary"] or "_No summary._")
            bl = core.list_budget_lines(p["id"])
            if bl:
                st.dataframe(pd.DataFrame([{
                    "Category": l["category"], "How it's spent": l["description"],
                    "Amount": core.money(l["amount"])} for l in bl]),
                    hide_index=True, use_container_width=True)
            if p["decided_at"]:
                st.caption(f'Decision: {p["status"]} — {p["decision_note"] or ""}')
idx += 1

# --- Review queue tab -------------------------------------------------------
if can_review:
    with tabs[idx]:
        queue = core.list_proposals(status="submitted")
        if not queue:
            st.info("Nothing awaiting review.")
        for p in queue:
            with st.expander(f'{p["title"]} · {p["director_name"]} · '
                             f'{core.money(p["requested_amount"])}', expanded=True):
                st.write(p["summary"] or "_No summary._")
                bl = core.list_budget_lines(p["id"])
                if bl:
                    st.dataframe(pd.DataFrame([{
                        "Category": l["category"], "How it's spent": l["description"],
                        "Amount": core.money(l["amount"])} for l in bl]),
                        hide_index=True, use_container_width=True)
                note = st.text_input("Decision note", key=f"note_{p['id']}")
                a, r = st.columns(2)
                if a.button("Approve", key=f"ap_{p['id']}", type="primary",
                            use_container_width=True):
                    core.decide_proposal(p["id"], True, user["id"], note)
                    st.success("Approved — project funded.")
                    st.rerun()
                if r.button("Reject", key=f"rj_{p['id']}",
                            use_container_width=True):
                    core.decide_proposal(p["id"], False, user["id"], note)
                    st.rerun()
