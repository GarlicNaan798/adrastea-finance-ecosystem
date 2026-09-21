"""Discussion — timestamped updates with a title/brief, newest first. Team
members (and their track director / founders) post; everyone reads."""
import streamlit as st

import core
import ui

st.set_page_config(page_title="Discussion · Adrastea", page_icon="🌘", layout="wide")
user = ui.require_login()
ui.page_header("Discussion", "Updates")

uid, role = user["id"], user["role"]
is_founder = role == "founder"
owned = core.owned_tracks(uid)
member_of = core.member_tracks(uid)

projects = core.list_projects()
if not projects:
    st.info("No projects yet. A director needs to create one first.")
    st.stop()


def can_post(track) -> bool:
    return is_founder or track in owned or track in member_of


postable = {f'{p["name"]}': p["id"] for p in projects if can_post(p["track"])}

# --- Post an update ---------------------------------------------------------
if postable:
    with st.container(border=True):
        st.subheader("Post an update")
        with st.form("post", clear_on_submit=True):
            c1, c2 = st.columns([2, 1.4])
            proj = c1.selectbox("Project", list(postable))
            status = c2.selectbox("Status", list(core.PROGRESS_STATUSES),
                                  format_func=lambda s: core.PROGRESS_LABELS[s])
            title = st.text_input("Brief / title", placeholder="e.g. Sensor array wired up")
            note = st.text_area("Details", height=90)
            if st.form_submit_button("Post", type="primary", width='stretch'):
                if not title.strip():
                    st.error("Add a short title.")
                else:
                    core.add_progress(postable[proj], uid, title, status, note.strip())
                    st.success("Posted.")
                    st.rerun()
else:
    st.caption("You can read updates below. To post, ask to be added to a track's team.")

# --- Timeline ---------------------------------------------------------------
st.subheader("Timeline")
names = {p["name"]: p["id"] for p in projects}
flt = st.selectbox("Filter", ["All projects"] + list(names))
pid = None if flt == "All projects" else names[flt]
feed = core.list_progress(project_id=pid, limit=200)
if not feed:
    st.caption("No updates yet.")
for g in feed:
    when = g["created_at"][:16].replace("T", " ")
    st.markdown(
        f'{ui.status_pill(g["status"])} &nbsp;**{g["title"] or "(untitled)"}** '
        f'<span class="meta">· {g["project_name"]} · {when} · '
        f'{g["author_name"] or "—"}</span>', unsafe_allow_html=True)
    if g["note"]:
        st.write(g["note"])
    ui.comment_thread("update", g["id"], user, can_post(g["track"]))
    st.divider()
