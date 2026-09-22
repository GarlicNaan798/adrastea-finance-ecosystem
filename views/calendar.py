"""Calendar — an agenda of every upcoming dated item you can see (milestones +
task due dates), grouped by date. The ManageBac 'everything dated in one place'."""
from itertools import groupby

import streamlit as st

import core
import ui


def calendar_view():
    ui.page_header("Calendar", "Deadlines")
    rows = [(m["due_date"], "Milestone", m["title"], m["project_name"], m["track"])
            for m in core.upcoming_milestones(limit=200)]
    rows += [(t["due_date"], "Task", t["title"], t["project_name"], t["track"])
             for t in core.list_tasks()
             if t["due_date"] and t["status"] != "done"]
    if not rows:
        st.info("Nothing scheduled. Add milestones or task due dates inside a project.")
        return
    rows.sort(key=lambda r: r[0])
    for due, items in groupby(rows, key=lambda r: r[0]):
        st.markdown(f"#### {due}")
        for _, kind, title, project, track in items:
            st.markdown(f'{kind} · **{title}** '
                        f'<span class="meta">· {project} · {track or "—"}</span>',
                        unsafe_allow_html=True)
