"""Adrastea — team project tracking.

Landing is a login-only screen; after sign-in the pages appear as a top navbar
(st.navigation, position="top"). Run: streamlit run app.py
"""
import streamlit as st

import core
import ui
import views

st.set_page_config(page_title="Adrastea", page_icon="🌘", layout="wide")
ui.apply_style()

user, ck = ui.auth()
if not user:                     # landing = just the Adrastea login, no nav
    ui.login_screen(ck)
    st.stop()

st.session_state.user = user     # views read the signed-in user from here
ui.sidebar(ck, user)

pages = {
    "home": st.Page(views.home, title="Home", icon="🏠", url_path="home", default=True),
    "projects": st.Page(views.projects, title="Projects", icon="📁", url_path="projects"),
    "calendar": st.Page(views.calendar_view, title="Calendar", icon="🗓️",
                        url_path="calendar"),
    "account": st.Page(views.account, title="Account", icon="⚙️", url_path="account"),
}
nav = [pages["home"], pages["projects"], pages["calendar"]]
if user["role"] == "founder" or core.owned_tracks(user["id"]):
    pages["team"] = st.Page(views.team, title="Team", icon="👥", url_path="team")
    nav.append(pages["team"])
nav.append(pages["account"])
st.session_state["_pages"] = pages

selected = st.navigation(nav, position="top")
# Leaving Projects drops the open project, so returning shows the list (not a stale
# workspace).
if getattr(selected, "url_path", "") != "projects":
    st.session_state.pop("open_project", None)
selected.run()
