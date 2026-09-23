"""Calendar — an agenda of every upcoming dated item you can see (milestones +
task due dates), grouped by date. The ManageBac 'everything dated in one place'."""
from itertools import groupby

import streamlit as st

import core
import ui


def calendar_view():
    ui.page_header("Calendar", "Deadlines")
    rows = [(m["due_date"], "Milestone", m["title"], m["project_name"], m["track"],
             m["project_id"], f"m{m['id']}") for m in core.upcoming_milestones(limit=200)]
    rows += [(t["due_date"], "Task", t["title"], t["project_name"], t["track"],
              t["project_id"], f"t{t['id']}")
             for t in core.list_tasks()
             if t["due_date"] and t["status"] != "done"]
    if not rows:
        ui.empty("Nothing scheduled. Add milestones or task due dates inside a project.")
        return
    rows.sort(key=lambda r: r[0])
    for due, items in groupby(rows, key=lambda r: r[0]):
        items = list(items)
        d = ui.as_date(due)
        ui.section(f"{d:%a} {ui.fmt_date(d)}" if d else due, len(items))
        for _, kind, title, project, track, pid, key in items:
            if ui.row(f"cal_{key}", title, f"{project} · {track or '—'}",
                      lead=f'<span class="adr-tag">{kind}</span>'):
                ui.open_project(pid)
        st.write("")
