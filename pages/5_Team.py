"""Team & tracks. Founders assign a director to each track. A track's director
(and founders) build that track's team from the full user pool and mark leads."""
import streamlit as st

import core
import ui

st.set_page_config(page_title="Team · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()

uid, role = user["id"], user["role"]
is_founder = role == "founder"
can_assign = core.can_assign_directors(role, user["email"])  # owner (Aiyana) only
owned = core.owned_tracks(uid)
if not (is_founder or owned):
    ui.page_header("Team", "Directory")
    st.error("Only founders and track directors manage the team.")
    st.stop()

ui.page_header("Team & tracks", "Directory")
people = core.list_profiles()
people_opts = {f'{u["name"]} · {u["email"]}': u["id"] for u in people}
directors = core.track_directors()

tabs = (["Track directors"] if can_assign else []) + ["Team by track"]
tab_objs = st.tabs(tabs)

# --- Owner: assign track directors ------------------------------------------
if can_assign:
    with tab_objs[0]:
        st.caption("Assign the director who runs each track. Directors come from "
                   "DIRECTOR_EMAILS; founders can direct a track too.")
        dir_people = [u for u in people if u["role"] in ("director", "founder")]
        dopts = {"— none —": None} | {f'{u["name"]} ({core.ROLE_LABELS[u["role"]]})':
                                      u["id"] for u in dir_people}
        if len(dopts) == 1:
            st.info("No directors yet. Add emails to DIRECTOR_EMAILS; meanwhile you "
                    "(founder) can manage every track's team in the next tab.")
        for track in core.TRACKS:
            cur = directors.get(track, {}).get("user_id")
            labels = list(dopts)
            idx = next((i for i, l in enumerate(labels) if dopts[l] == cur), 0)
            c1, c2 = st.columns([3, 1])
            sel = c1.selectbox(track, labels, index=idx, key=f"dir_{track}")
            if c2.button("Save", key=f"dsave_{track}", width='stretch'):
                core.set_track_director(track, dopts[sel])
                st.success(f"Director set for {track}.")
                st.rerun()

# --- Build each track's team ------------------------------------------------
with tab_objs[-1]:
    my_tracks = list(core.TRACKS) if is_founder else sorted(owned)
    st.caption("Add people to a track's team. Mark **leads** (they can edit that "
               "track's projects); other members post updates and hold tasks.")
    for track in my_tracks:
        with st.expander(track, expanded=(len(my_tracks) == 1)):
            members = core.list_track_members(track)
            cur_ids = {m["user_id"] for m in members}
            cur_leads = {m["user_id"] for m in members if m["is_lead"]}
            mdefault = [l for l, i in people_opts.items() if i in cur_ids]
            ldefault = [l for l, i in people_opts.items() if i in cur_leads]
            chosen = st.multiselect("Team members", list(people_opts),
                                    default=mdefault, key=f"mem_{track}")
            leads = st.multiselect("Leads (must also be team members)",
                                   list(people_opts), default=ldefault,
                                   key=f"lead_{track}")
            if st.button("Save team", key=f"tsave_{track}", width='stretch'):
                chosen_ids = {people_opts[l] for l in chosen}
                lead_ids = {people_opts[l] for l in leads} & chosen_ids
                for i in chosen_ids:
                    core.add_track_member(track, i, is_lead=(i in lead_ids))
                for i in cur_ids - chosen_ids:
                    core.remove_track_member(track, i)
                st.success(f"Team updated for {track}.")
                st.rerun()
