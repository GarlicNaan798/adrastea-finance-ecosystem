"""Calendar — every open, dated item grouped by date (milestones + task due
dates), plus a 'No date set' group so undated work is still visible and you're
nudged to add a deadline. Click any row to open its project."""
from itertools import groupby

import streamlit as st

import core
import ui


def calendar_view():
    ui.page_header("Calendar", "Deadlines")

    # (due_date|None, kind, title, project, track, project_id, key)
    items = [(m["due_date"], "Milestone", m["title"], m["project_name"], m["track"],
              m["project_id"], f"m{m['id']}") for m in core.incomplete_milestones()]
    items += [(t["due_date"], "Task", t["title"], t["project_name"], t["track"],
               t["project_id"], f"t{t['id']}")
              for t in core.list_tasks() if t["status"] != "done"]

    dated = sorted((i for i in items if i[0]), key=lambda r: r[0])
    undated = [i for i in items if not i[0]]

    if not dated and not undated:
        ui.empty("Nothing scheduled yet. Create tasks or milestones in a project — "
                 "give them a due date and they'll show up here by date.")
        return

    def _rows(group):
        for _, kind, title, project, track, pid, key in group:
            if ui.row(f"cal_{key}", title, f"{project} · {track or '—'}",
                      lead=f'<span class="adr-tag">{kind}</span>'):
                ui.open_project(pid)

    for due, group in groupby(dated, key=lambda r: r[0]):
        group = list(group)
        d = ui.as_date(due)
        ui.section(f"{d:%a} {ui.fmt_date(d)}" if d else due, len(group))
        _rows(group)
        st.write("")

    if undated:
        ui.section("No date set", len(undated), "Open one to add a deadline")
        _rows(undated)
        st.write("")
