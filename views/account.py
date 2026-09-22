"""Account: your role and password."""
import streamlit as st

import core
import ui

_ROLE_NOTE = {
    "founder": "As a founder you manage everything: build any track's team and run all "
               "projects. Appointing track directors is limited to the owner.",
    "director": "As a director you run the track(s) you're assigned — create projects, "
                "set budgets, build your team and assign tasks there.",
    "member": "You contribute on the track team(s) you're added to: post updates and "
              "work assigned tasks. A director can make you a **lead** to edit that "
              "track's projects.",
}


def account():
    user = st.session_state.user
    ui.page_header("Account", "Settings")
    st.write(f"**{user['name']}** · {user['email']}")
    st.write(f"Role: **{core.ROLE_LABELS.get(user['role'], user['role'])}**")
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
