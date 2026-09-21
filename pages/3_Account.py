"""Account: your role and password."""
import streamlit as st

import core
import ui

st.set_page_config(page_title="Account · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Account", "Settings")

st.write(f"**{user['name']}** · {user['email']}")
st.write(f"Role: **{core.ROLE_LABELS.get(user['role'], user['role'])}**")
_ROLE_NOTE = {
    "director": "As a director you can create/delete projects, set budgets, assign "
                "leads, and promote specialists (Team page).",
    "specialist": "As a specialist you can edit any project's details, "
                  "requirements, status and progress. Budgets stay director-only.",
    "member": "You can view projects and post weekly progress. A director can make "
              "you a project **lead** (edit that project) or a **specialist**.",
}
st.caption(_ROLE_NOTE.get(user["role"], _ROLE_NOTE["member"]))

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
