"""Weekly progress: any member posts an update; everyone sees the timeline."""
from datetime import date

import streamlit as st

import core
import ui

st.set_page_config(page_title="Progress · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Progress", "This week")

projects = core.list_projects()
if not projects:
    st.info("No projects to update yet. A director needs to create one first.")
    st.stop()

proj_by_label = {f'{p["name"]}': p["id"] for p in projects}

# --- Post an update ---------------------------------------------------------
with st.container(border=True):
    st.subheader("Post an update")
    with st.form("progress", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1.4, 1.2])
        proj_label = c1.selectbox("Project", list(proj_by_label))
        status = c2.selectbox("Status", list(core.PROGRESS_STATUSES),
                              format_func=lambda s: core.PROGRESS_LABELS[s])
        when = c3.date_input("Week of", value=date.today())
        note = st.text_area("What happened this week?", height=90)
        if st.form_submit_button("Post update", type="primary",
                                 width='stretch'):
            if not note.strip():
                st.error("Add a short note.")
            else:
                core.add_progress(proj_by_label[proj_label], user["id"], status,
                                  note.strip(), core.week_monday(when))
                st.success("Update posted.")
                st.rerun()

# --- Timeline ---------------------------------------------------------------
st.subheader("Timeline")
flt = st.selectbox("Filter", ["All projects"] + list(proj_by_label))
pid = None if flt == "All projects" else proj_by_label[flt]
feed = core.list_progress(project_id=pid, limit=100)

if not feed:
    st.caption("No updates yet.")
for g in feed:
    st.markdown(
        f'{ui.status_pill(g["status"])} &nbsp;**{g["project_name"]}** '
        f'<span class="meta">· week of {g["week_start"]} · '
        f'{g["author_name"] or "—"}</span>', unsafe_allow_html=True)
    if g["note"]:
        st.write(g["note"])
    st.divider()
