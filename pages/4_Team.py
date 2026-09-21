"""Team & tracks (directors only): promote specialists, assign track leads,
set track coordinators."""
import streamlit as st

import core
import ui

st.set_page_config(page_title="Team · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.require_role(user, "director")
ui.page_header("Team & tracks", "Directory")

people = core.list_profiles()
tiers = list(core.ASSIGNABLE_TIERS)

t_people, t_tracks = st.tabs(["People", "Tracks"])

# --- People: tiers ----------------------------------------------------------
with t_people:
    st.caption("Directors come from the organisation's allowlist. Promote anyone "
               "else between Member and Specialist. Specialists can edit any "
               "project's details across all tracks.")
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

# --- Tracks: coordinators + leads -------------------------------------------
with t_tracks:
    st.caption("Each track has a coordinator (a director) and leads. Leads can "
               "edit projects in their track; directors and specialists can edit "
               "any track.")
    directors = [u for u in people if u["role"] == "director"]
    coords = core.track_coordinators()
    people_opts = {f'{u["name"]} · {u["email"]}': u["id"] for u in people}
    dir_opts = {"— none —": None} | {f'{u["name"]}': u["id"] for u in directors}

    for track in core.TRACKS:
        with st.expander(track, expanded=(track == "CHASM Project")):
            # Coordinator
            cur_owner = coords.get(track, {}).get("user_id")
            labels = list(dir_opts)
            idx = next((i for i, lbl in enumerate(labels)
                        if dir_opts[lbl] == cur_owner), 0)
            csel = st.selectbox("Coordinator (director)", labels, index=idx,
                                key=f"coord_{track}")
            if st.button("Save coordinator", key=f"savecoord_{track}"):
                core.set_track_coordinator(track, dir_opts[csel])
                st.success(f"Coordinator set for {track}.")
                st.rerun()

            # Leads
            current = {l["user_id"] for l in core.list_track_leads(track)}
            default = [lbl for lbl, uid in people_opts.items() if uid in current]
            chosen = st.multiselect("Track leads", list(people_opts), default=default,
                                    key=f"leads_{track}")
            if st.button("Save leads", key=f"saveleads_{track}", width='stretch'):
                chosen_ids = {people_opts[l] for l in chosen}
                for uid in chosen_ids - current:
                    core.assign_track_lead(track, uid)
                for uid in current - chosen_ids:
                    core.remove_track_lead(track, uid)
                st.success(f"Leads updated for {track}.")
                st.rerun()
