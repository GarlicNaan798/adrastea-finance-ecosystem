"""Account settings for everyone; role management for admins."""
import streamlit as st

import core
import ui

st.set_page_config(page_title="Admin · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Admin & account", "Settings")

# --- Everyone: change own password (via Supabase Auth) ----------------------
st.markdown("#### Change my password")
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

if user["role"] != "admin":
    st.stop()

st.divider()
st.markdown("#### People & roles")
st.caption("New users sign up themselves and start as **pending**. Grant them a "
           "role here. Set a role to *pending* to revoke access.")

for u in core.list_profiles():
    tag = "🕓 pending" if u["role"] == "pending" else u["role"]
    with st.expander(f'{u["name"]} · {u["email"]} · {tag}',
                     expanded=(u["role"] == "pending")):
        c1, c2 = st.columns([3, 1])
        options = list(core.ALL_ROLES)
        new_role = c1.selectbox("Role", options,
                                index=options.index(u["role"]),
                                key=f"role_{u['id']}")
        if c2.button("Save", key=f"save_{u['id']}", use_container_width=True):
            core.set_role(u["id"], new_role)
            st.success(f'{u["name"]} is now {new_role}.')
            st.rerun()
