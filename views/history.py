"""Combined update history — every project's updates in one feed, newest first,
filterable by track/status. Read-only (post & comment inside a project's Updates
tab); each row opens its project."""
import streamlit as st

import core
import ui

_SC = {"on_track": "green", "at_risk": "orange", "blocked": "red", "done": "blue"}


def _open(pid):
    st.session_state.open_project = pid
    st.switch_page(st.session_state["_pages"]["projects"])


def history():
    ui.page_header("Update history", "Activity")
    feed = core.list_progress(limit=500)
    if not feed:
        st.info("No updates yet. Post updates in a project's **Updates** tab.")
        return

    tracks = sorted({g["track"] for g in feed if g["track"]})
    c1, c2 = st.columns(2)
    trk = c1.selectbox("Track", ["All tracks"] + tracks)
    status = c2.selectbox("Status", ["All statuses"] + list(core.PROGRESS_STATUSES),
                          format_func=lambda s: core.PROGRESS_LABELS.get(s, s))
    rows = [g for g in feed
            if (trk == "All tracks" or g["track"] == trk)
            and (status == "All statuses" or g["status"] == status)]
    st.caption(f"{len(rows)} update(s) · newest first · click one to open its project")

    for g in rows:
        when = g["created_at"][:16].replace("T", " ")
        if st.button(
            f':{_SC.get(g["status"], "gray")}'
            f'[{core.PROGRESS_LABELS.get(g["status"], g["status"])}]'
            f' · **{g["title"] or "(untitled)"}** · {g["project_name"]}'
            f' · {when} · {g["author_name"] or "—"}',
                key=f"nav_hist_{g['id']}", width='stretch'):
            _open(g["project_id"])
        if g["note"]:
            st.caption(g["note"])
