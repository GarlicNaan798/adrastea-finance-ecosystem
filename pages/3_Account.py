"""Account: your role and password."""
import streamlit as st

import core
import ui

st.set_page_config(page_title="Account · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Account", "Settings")

st.write(f"**{user['name']}** · {user['email']}")
st.write(f"Role: **{user['role']}**")
if user["role"] == "director":
    st.caption("As a director you can create and edit projects, requirements and "
               "budgets on the Projects page.")
else:
    st.caption("Members can view projects and post weekly progress. Directors are "
               "set by the organisation; ask an admin to be added.")

st.divider()
st.subheader("Change my password")
with st.form("mypw", clear_on_submit=True):
    new = st.text_input("New password (8+ chars)", type="password")
    confirm = st.text_input("Confirm", type="password")
    if st.form_submit_button("Update password"):
        if len(new) < 8:
            st.error("Use at least 8 characters.")
        elif new != confirm:
            st.error("Passwords don't match.")
        else:
            ok, msg = core.change_password(user["access_token"], new)
            (st.success if ok else st.error)(msg)
