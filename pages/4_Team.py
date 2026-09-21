"""Team directory. Directors promote members to specialists (and back)."""
import streamlit as st

import core
import ui

st.set_page_config(page_title="Team · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.require_role(user, "director")
ui.page_header("Team", "Directory")

st.caption("Directors come from the organisation's allowlist. You can promote "
           "anyone else between **Member** and **Specialist**. Specialists can "
           "edit any project's details; assign project **leads** on the Projects page.")

people = core.list_profiles()
tiers = list(core.ASSIGNABLE_TIERS)

for u in people:
    c1, c2, c3 = st.columns([3, 1.4, 1])
    c1.markdown(f"**{u['name']}**  \n<span class='meta'>{u['email']}</span>",
                unsafe_allow_html=True)
    if u["role"] == "director":
        c2.markdown("**Director**")
        c3.caption("allowlist")
        continue
    new_tier = c2.selectbox(
        "Tier", tiers, index=tiers.index(u["role"]) if u["role"] in tiers else 0,
        format_func=lambda t: core.ROLE_LABELS[t], key=f"tier_{u['id']}",
        label_visibility="collapsed")
    if c3.button("Save", key=f"save_{u['id']}", width='stretch',
                 disabled=(new_tier == u["role"])):
        core.set_tier(u["id"], new_tier)
        st.success(f"{u['name']} is now a {core.ROLE_LABELS[new_tier]}.")
        st.rerun()
    st.divider()
