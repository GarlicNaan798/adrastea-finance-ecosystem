"""Shared Streamlit layer: brand, styling, Supabase login/sign-up, role guards."""
from __future__ import annotations

import streamlit as st
from streamlit_cookies_controller import CookieController

import core

# Palette (kept in sync with .streamlit/config.toml and the brand kit)
PAPER, INK, CLAY, NAVY, STONE = "#FBFAF7", "#23211C", "#9E6B4B", "#17263A", "#E7E3D8"

# Persistent login: a rotating Supabase refresh token stored in a browser cookie,
# so a hard refresh restores the session instead of logging out.
_COOKIE = "adr_session"
_COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 days


def _cookies():
    try:
        return CookieController()
    except Exception:  # cookie layer is always optional — never break login
        return None


def _save_session(ck, sess: dict) -> None:
    if ck is not None:
        try:
            ck.set(_COOKIE, sess["refresh_token"], max_age=_COOKIE_MAX_AGE)
        except Exception:
            pass


def _restore_session(ck) -> dict | None:
    """Rebuild the user from the refresh-token cookie, if present and valid."""
    if ck is None:
        return None
    try:
        rt = ck.get(_COOKIE)
    except Exception:
        return None
    if not rt:
        return None
    sess = core.refresh_session(rt)  # needs live Supabase; None if unreachable
    if not sess:
        try:
            ck.remove(_COOKIE)
        except Exception:
            pass
        return None
    prof = core.get_profile(sess["id"])
    st.session_state.user = {
        **sess,
        "name": prof["name"] if prof else sess["email"],
        "role": prof["role"] if prof else "pending",
    }
    _save_session(ck, sess)  # persist the rotated token
    return st.session_state.user


def mark(size: int = 34, color: str = INK) -> str:
    """Inline Adrastea mark: an 'A' whose crossbar is an orbit, moon on it."""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 100 100" '
        f'style="display:block;flex:none">'
        f'<path d="M18 86 L50 15 L82 86" fill="none" stroke="{color}" '
        f'stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<ellipse cx="50" cy="56" rx="40" ry="13" fill="none" stroke="{CLAY}" '
        f'stroke-width="3.6" transform="rotate(-18 50 56)"/>'
        f'<circle cx="88" cy="44" r="5.4" fill="{CLAY}"/></svg>'
    )


_STYLE = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="st-"], input, textarea, select, button {{
    font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
}}
/* Keep Streamlit's Material icons as glyphs — the broad rule above would
   otherwise render them as their ligature text ("visibility", the sidebar's
   "keyboard_double_arrow_left"), which also overflows into nearby elements. */
[data-testid="stIconMaterial"], span.material-symbols-rounded,
span.material-symbols-outlined {{ font-family: 'Material Symbols Rounded' !important; }}
h1, h2, h3 {{ font-family: 'Fraunces', Georgia, serif; letter-spacing: -0.01em; }}
h1 {{ font-weight: 600; }} h2, h3 {{ font-weight: 500; }}

.block-container {{ max-width: 1180px; padding-top: 2.4rem; padding-bottom: 4rem; }}

#MainMenu, [data-testid="stToolbar"], [data-testid="stDecoration"],
.stDeployButton, footer {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent; }}

/* Brand bits */
.overline {{ font-size: .72rem; letter-spacing: .2em; text-transform: uppercase;
    color: {CLAY}; font-weight: 600; margin: 0 0 .1rem 2px; }}
.brandbar {{ display:flex; align-items:center; gap:.55rem; padding:.1rem 0 1rem; }}
.brandbar .name {{ font-family:'Fraunces',Georgia,serif; font-size:1.45rem;
    font-weight:600; color:{INK}; letter-spacing:-.01em; }}

/* Flat, quiet metrics */
[data-testid="stMetric"] {{ background: transparent; padding: 0; }}
[data-testid="stMetricLabel"] p {{ opacity:.6; text-transform:uppercase;
    letter-spacing:.07em; font-size:.72rem; }}
[data-testid="stMetricValue"] {{ font-family:'Fraunces',Georgia,serif; font-weight:500; }}

/* Cards / bordered containers */
[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:14px; }}

/* Minimal buttons */
.stButton > button, .stFormSubmitButton > button {{
    border-radius:8px; box-shadow:none; font-weight:500; }}

/* Subtle separations */
[data-testid="stSidebar"] {{ border-right:1px solid rgba(0,0,0,.06); }}
[data-testid="stExpander"] {{ border-radius:10px; }}
hr {{ margin:1.3rem 0; opacity:.5; }}
.stTabs [data-baseweb="tab-list"] {{ gap:1.6rem; }}
</style>
"""


def apply_style() -> None:
    st.markdown(_STYLE, unsafe_allow_html=True)


def page_header(title: str, overline: str | None = None) -> None:
    if overline:
        st.markdown(f'<div class="overline">{overline}</div>', unsafe_allow_html=True)
    st.markdown(f"# {title}")


def _auth_screen(ck) -> None:
    _, mid, _ = st.columns([1, 1.35, 1])
    with mid:
        st.markdown(
            f'<div style="text-align:center;padding:1.2rem 0 .4rem">'
            f'<div style="display:flex;justify-content:center">{mark(58)}</div>'
            f'<div style="font-family:\'Fraunces\',Georgia,serif;font-size:2.4rem;'
            f'font-weight:600;color:{INK};margin-top:.5rem">Adrastea</div>'
            f'<div style="font-size:.72rem;letter-spacing:.28em;color:{CLAY};'
            f'margin-top:.2rem">RESEARCH&nbsp;&nbsp;FOUNDATION</div>'
            f'<div style="font-family:\'Fraunces\',Georgia,serif;font-style:italic;'
            f'color:rgba(35,33,28,.55);margin-top:.9rem">Research, held to account.</div>'
            f'</div>', unsafe_allow_html=True)
        st.write("")
        signin, signup = st.tabs(["Sign in", "Create account"])

        with signin:
            with st.form("signin"):
                email = st.text_input("Email")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Sign in", use_container_width=True,
                                         type="primary"):
                    sess = core.sign_in(email, pw)
                    if not sess:
                        st.error("Invalid email or password.")
                    else:
                        prof = core.get_profile(sess["id"])
                        st.session_state.user = {
                            **sess,
                            "name": prof["name"] if prof else sess["email"],
                            "role": prof["role"] if prof else "pending",
                        }
                        _save_session(ck, sess)  # remember me across refreshes
                        st.rerun()

        with signup:
            with st.form("signup"):
                name = st.text_input("Full name")
                email = st.text_input("Email", key="su_email")
                pw = st.text_input("Password (8+ chars)", type="password", key="su_pw")
                if st.form_submit_button("Create account", use_container_width=True):
                    if not (name and email and len(pw) >= 8):
                        st.error("Name, email, and an 8+ character password required.")
                    else:
                        ok, msg = core.sign_up(email, pw, name)
                        (st.success if ok else st.error)(msg)


def require_login() -> dict:
    """Render auth if needed; return the current user. Gates 'pending' accounts."""
    apply_style()
    ck = _cookies()
    user = st.session_state.get("user") or _restore_session(ck)
    if not user:
        _auth_screen(ck)
        st.stop()
    _sidebar(ck, user)
    if user["role"] == "pending":
        page_header("Awaiting access", "Adrastea")
        st.info("Your account is pending. An administrator will grant you a role "
                "shortly — then Proposals, Projects and Finance will unlock.")
        st.stop()
    return user


def require_role(user: dict, *roles: str) -> None:
    if user["role"] not in roles:
        st.error("You don't have access to this page.")
        st.stop()


def _sidebar(ck, user: dict) -> None:
    with st.sidebar:
        st.markdown(
            f'<div class="brandbar">{mark(30)}<span class="name">Adrastea</span></div>',
            unsafe_allow_html=True)
        st.markdown(f"**{user['name']}**")
        st.caption(f"{user['email']} · {user['role']}")
        if st.button("Sign out", use_container_width=True):
            core.sign_out(user.get("access_token", ""))
            if ck is not None:
                try:
                    ck.remove(_COOKIE)
                except Exception:
                    pass
            del st.session_state.user
            st.rerun()
