"""Adrastea — team project tracking.

Landing is a login-only screen; after sign-in the pages appear as a collapsible
left navbar (st.navigation, position="sidebar" — "top" isn't rendered by this
Streamlit build). Run: streamlit run app.py
"""
import streamlit as st

import core
import ui
import views

st.set_page_config(page_title="Adrastea", page_icon="🌘", layout="wide")
ui.apply_style()

missing = core.missing_config()
if missing:
    st.error(
        "This app isn't fully configured. Missing secret(s): **"
        + ", ".join(missing) + "**.\n\n"
        "Add them under **Manage app → Settings → Secrets** (Streamlit Cloud) or in "
        "`.streamlit/secrets.toml` locally. Every `KEY = \"...\"` line must sit "
        "**above** the `[TRACK_DIRECTORS]` table — a TOML table captures every line "
        "after it, which hides keys placed below it.")
    st.stop()

user, ck = ui.auth()
if not user:                     # landing = just the Adrastea login, no nav
    ui.login_screen(ck)
    st.stop()

st.session_state.user = user     # views read the signed-in user from here
ui.sidebar(ck, user)

pages = {
    "home": st.Page(views.home, title="Home", icon=":material/home:", url_path="home", default=True),
    "projects": st.Page(views.projects, title="Projects", icon=":material/folder_open:", url_path="projects"),
    "history": st.Page(views.history, title="History", icon=":material/history:", url_path="history"),
    "calendar": st.Page(views.calendar_view, title="Calendar", icon=":material/calendar_month:",
                        url_path="calendar"),
    "account": st.Page(views.account, title="Account", icon=":material/settings:", url_path="account"),
}
nav = [pages["home"], pages["projects"], pages["history"], pages["calendar"]]
if user["role"] == "founder" or core.owned_tracks(user["id"]):
    pages["team"] = st.Page(views.team, title="Team", icon=":material/group:", url_path="team")
    nav.append(pages["team"])
nav.append(pages["account"])
st.session_state["_pages"] = pages

selected = st.navigation(nav, position="sidebar")
# Leaving Projects drops the open project, so returning shows the list (not a stale
# workspace).
if getattr(selected, "url_path", "") != "projects":
    st.session_state.pop("open_project", None)
selected.run()
