"""Meeting notes. Team leads, directors and founders post a dated note — title,
summary and an optional link to the full notes. Everyone can read them."""
from datetime import date
from html import escape

import streamlit as st

import core
import ui

_GENERAL = "— General —"


def meetings():
    user = st.session_state.user
    uid, role = user["id"], user["role"]
    is_founder = role == "founder"
    owned, led = core.owned_tracks(uid), core.lead_tracks(uid)
    can_post = is_founder or bool(owned) or bool(led)
    ui.page_header("Meeting notes", "Minutes")

    if can_post:
        opts = ([_GENERAL] + list(core.TRACKS) if is_founder
                else [_GENERAL] + sorted(set(owned) | set(led)))
        with st.form("mn", clear_on_submit=True):
            title = st.text_input("Meeting title", placeholder="e.g. Weekly Bioeng sync")
            c1, c2 = st.columns(2)
            mdate = c1.date_input("Meeting date", value=date.today())
            track = c2.selectbox("Track", opts)
            summary = st.text_area("Summary", height=100,
                                   placeholder="What was discussed and decided…")
            url = st.text_input("Notes link (optional)",
                                placeholder="https://docs.google.com/…")
            if st.form_submit_button("Post meeting notes", type="primary", width='stretch'):
                if not title.strip():
                    st.error("Add a meeting title.")
                elif url.strip() and not core.clean_url(url):
                    st.error("The notes link must be a valid http(s) URL (or leave it blank).")
                else:
                    core.add_meeting_note(
                        title, mdate.isoformat() if isinstance(mdate, date) else None,
                        summary, url.strip(), None if track == _GENERAL else track, uid)
                    st.success("Posted.")
                    st.rerun()
    else:
        ui.empty("Team leads and directors post meeting notes here; everyone can read them.")

    notes = core.list_meeting_notes()
    ui.section("Meeting notes", len(notes))
    if not notes:
        ui.empty("No meeting notes yet.")
    for n in notes:
        _note(n, user, is_founder)


def _note(n, user, is_founder):
    can_del = is_founder or n["author_id"] == user["id"]
    track = n["track"] or "General"
    summary = f'<div class="note">{escape(n["summary"])}</div>' if n["summary"] else ""
    link = (f'<div style="margin-top:.4rem">{ui.doc_row("Full notes", n["url"])}</div>'
            if n["url"] else "")
    html = (f'<div class="adr-log"><div class="when">{ui.fmt_date(n["meeting_date"])}</div>'
            f'<div class="body"><div class="head">'
            f'<span class="adr-tag">{escape(track)}</span><b>{escape(n["title"])}</b></div>'
            f'{summary}{link}<div class="by">{escape(n["author_name"] or "—")}</div>'
            f'</div></div>')
    if can_del:
        a, b = st.columns([7, 1])
        a.markdown(html, unsafe_allow_html=True)
        if b.button("Remove", key=f"mnrm_{n['id']}"):
            core.remove_meeting_note(n["id"])
            st.rerun()
    else:
        st.markdown(html, unsafe_allow_html=True)
