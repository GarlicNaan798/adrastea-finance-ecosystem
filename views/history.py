"""Combined update history — every project's updates in one feed, newest first,
filterable by track/status. Read-only (post & comment inside a project's Updates
tab); each row opens its project."""
import streamlit as st

import core
import ui


def history():
    ui.page_header("Update history", "Activity")
    feed = core.list_progress(limit=500)
    if not feed:
        ui.empty("No updates yet. Post updates in a project's Updates tab.")
        return

    tracks = sorted({g["track"] for g in feed if g["track"]})
    c1, c2 = st.columns(2)
    trk = c1.selectbox("Track", ["All tracks"] + tracks)
    status = c2.selectbox("Status", ["All statuses"] + list(core.PROGRESS_STATUSES),
                          format_func=lambda s: core.PROGRESS_LABELS.get(s, s))
    rows = [g for g in feed
            if (trk == "All tracks" or g["track"] == trk)
            and (status == "All statuses" or g["status"] == status)]
    ui.section("Updates", len(rows))

    for g in rows:
        if ui.row(f"hist_{g['id']}", g["title"] or "(untitled)",
                  f'{g["project_name"]} · {g["author_name"] or "—"}'
                  + (f' — {g["note"]}' if g["note"] else ""),
                  lead=ui.status_pill(g["status"]), aside=ui.when(g["created_at"])):
            ui.open_project(g["project_id"])
