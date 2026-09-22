"""Shared Streamlit layer: brand, styling, Supabase login/sign-up, role guards.

Colors come from native Streamlit theming (.streamlit/config.toml, light + dark).
This module only adds brand bits and a few theme-aware tokens (--adr-*).
"""
from __future__ import annotations

import streamlit as st
from streamlit_cookies_controller import CookieController

import core

# Light-mode reference values (charts etc.); UI colors come from config theme.
PAPER, INK, CLAY, NAVY, STONE = "#FBFAF7", "#23211C", "#9E6B4B", "#17263A", "#E7E3D8"

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
    prof = core.sync_profile(sess["id"], sess["email"])  # role from allowlist
    st.session_state.user = {**sess, "name": prof["name"], "role": prof["role"]}
    _save_session(ck, sess)
    return st.session_state.user


def mark(size: int = 34) -> str:
    """Inline Adrastea mark. 'A' inherits currentColor; orbit/moon use the
    theme accent, so it reads correctly in both light and dark."""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 100 100" '
        f'style="display:block;flex:none" aria-hidden="true">'
        f'<path d="M18 86 L50 15 L82 86" fill="none" stroke="currentColor" '
        f'stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<ellipse cx="50" cy="56" rx="40" ry="13" fill="none" stroke="var(--adr-accent)" '
        f'stroke-width="3.6" transform="rotate(-18 50 56)"/>'
        f'<circle cx="88" cy="44" r="5.4" fill="var(--adr-accent)"/></svg>'
    )


_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');

:root { --adr-accent:#7E4F33; --adr-muted:#635D53; --adr-ink:#23211C;
        --adr-hair:rgba(35,33,28,.10); }
@media (prefers-color-scheme: dark) {
  :root { --adr-accent:#C08A63; --adr-muted:#A79E90; --adr-ink:#ECE7DD;
          --adr-hair:rgba(255,255,255,.12); }
}

.block-container { max-width: 1180px; padding-top: 2.4rem; padding-bottom: 4rem; }

/* Hide Streamlit chrome for a cleaner, app-like surface */
#MainMenu, [data-testid="stToolbar"], [data-testid="stDecoration"],
.stDeployButton, footer { display: none !important; }
[data-testid="stHeader"] { background: transparent; }

/* Quiet, flat metrics */
[data-testid="stMetric"] { background: transparent; padding: 0; }
[data-testid="stMetricLabel"] p { text-transform: uppercase; letter-spacing: .07em;
  font-size: .72rem; color: var(--adr-muted); }
[data-testid="stMetricValue"] { font-family: 'Fraunces', Georgia, serif; font-weight: 500; }

/* Accessible muted text */
.meta { color: var(--adr-muted); }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--adr-muted); }

/* Brand */
.overline { font-size: .72rem; letter-spacing: .2em; text-transform: uppercase;
  color: var(--adr-accent); font-weight: 600; margin: 0 0 .1rem 2px; }
.brandbar { display: flex; align-items: center; gap: .55rem; padding: .1rem 0 1rem;
  color: var(--adr-ink); }
.brandbar .name { font-family: 'Fraunces', Georgia, serif; font-size: 1.45rem;
  font-weight: 600; letter-spacing: -.01em; }

/* Subtle separations */
[data-testid="stSidebar"] { border-right: 1px solid var(--adr-hair); }
[data-testid="stExpander"] { border-radius: 12px; }
hr { margin: 1.3rem 0; opacity: .5; }
.stTabs [data-baseweb="tab-list"] { gap: 1.6rem; }

/* Accessibility: visible keyboard focus on every interactive element */
a:focus-visible, button:focus-visible, input:focus-visible, textarea:focus-visible,
select:focus-visible, [role="tab"]:focus-visible, [role="button"]:focus-visible,
[data-baseweb="tab"]:focus-visible, summary:focus-visible {
  outline: 2px solid var(--adr-accent); outline-offset: 2px; border-radius: 4px;
}

/* Dark mode uses a light clay primary, so give primary buttons dark label text
   (white-on-clay fails WCAG AA; dark-on-clay passes at 6:1). */
@media (prefers-color-scheme: dark) {
  [data-testid^="stBaseButton-primary"],
  [data-testid^="stBaseButton-primary"] * { color: #1A1714 !important; }
}
</style>
"""


def apply_style() -> None:
    st.markdown(_STYLE, unsafe_allow_html=True)


def page_header(title: str, overline: str | None = None) -> None:
    if overline:
        st.markdown(f'<div class="overline">{overline}</div>', unsafe_allow_html=True)
    st.markdown(f"# {title}")


# Solid pills with white text — pass WCAG AA in both light and dark.
_STATUS_COLORS = {"on_track": "#2F6B4F", "at_risk": "#8A5A1E",
                  "blocked": "#9B3D33", "done": "#3A4A5E"}


def status_pill(status: str) -> str:
    label = core.PROGRESS_LABELS.get(status, status)
    c = _STATUS_COLORS.get(status, "#555")
    return (f'<span style="background:{c};color:#fff;border-radius:999px;'
            f'padding:.14rem .62rem;font-size:.72rem;font-weight:600;'
            f'white-space:nowrap">{label}</span>')


def comment_thread(parent_type: str, parent_id: int, user: dict,
                   can_comment: bool, key_suffix: str = "") -> None:
    """Collapsible comment thread under a discussion update or a task.
    key_suffix disambiguates when the same item renders in two places."""
    comments = core.list_comments(parent_type, parent_id)
    with st.expander(f"Comments ({len(comments)})"):
        for c in comments:
            when = c["created_at"][:16].replace("T", " ")
            st.markdown(f'**{c["author_name"] or "—"}** '
                        f'<span class="meta">· {when}</span>', unsafe_allow_html=True)
            st.write(c["body"])
        if can_comment:
            with st.form(f"cmt_{parent_type}_{parent_id}_{key_suffix}",
                         clear_on_submit=True):
                body = st.text_area("Reply", height=68, label_visibility="collapsed",
                                    placeholder="Write a reply…")
                if st.form_submit_button("Reply"):
                    if body.strip():
                        core.add_comment(parent_type, parent_id, user["id"], body)
                        st.rerun()
        elif not comments:
            st.caption("No comments yet.")


def login_screen(ck) -> None:
    """The landing: a clean, centered Adrastea login (no nav tabs until signed in)."""
    _, mid, _ = st.columns([1, 1.35, 1])
    with mid:
        st.markdown(
            f'<div style="text-align:center;padding:1.2rem 0 .4rem;color:var(--adr-ink)">'
            f'<div style="display:flex;justify-content:center">{mark(58)}</div>'
            f'<div style="font-family:\'Fraunces\',Georgia,serif;font-size:2.4rem;'
            f'font-weight:600;margin-top:.5rem">Adrastea</div>'
            f'<div style="font-size:.72rem;letter-spacing:.24em;color:var(--adr-accent);'
            f'margin-top:.2rem;white-space:nowrap">RESEARCH&nbsp;&nbsp;FOUNDATION</div>'
            f'<div style="font-family:\'Fraunces\',Georgia,serif;font-style:italic;'
            f'color:var(--adr-muted);margin-top:.9rem">Research, held to account.</div>'
            f'</div>', unsafe_allow_html=True)
        st.write("")
        signin, signup = st.tabs(["Sign in", "Create account"])

        with signin:
            with st.form("signin"):
                email = st.text_input("Email")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Sign in", width='stretch', type="primary"):
                    sess = core.sign_in(email, pw)
                    if not sess:
                        st.error("Invalid email or password.")
                    else:
                        prof = core.sync_profile(sess["id"], sess["email"])
                        st.session_state.user = {**sess, "name": prof["name"],
                                                 "role": prof["role"]}
                        _save_session(ck, sess)
                        st.rerun()

        with signup:
            with st.form("signup"):
                name = st.text_input("Full name")
                email = st.text_input("Email", key="su_email")
                pw = st.text_input("Password (8+ chars)", type="password", key="su_pw")
                if st.form_submit_button("Create account", width='stretch'):
                    if not (name and email and len(pw) >= 8):
                        st.error("Name, email, and an 8+ character password required.")
                    else:
                        ok, msg = core.sign_up(email, pw, name)
                        (st.success if ok else st.error)(msg)


def auth():
    """Return (user_or_None, cookie_controller). No rendering — the caller shows
    login_screen() when user is None, else registers the navbar."""
    ck = _cookies()
    user = st.session_state.get("user") or _restore_session(ck)
    return user, ck


def sidebar(ck, user: dict) -> None:
    with st.sidebar:
        st.markdown(
            f'<div class="brandbar">{mark(30)}<span class="name">Adrastea</span></div>',
            unsafe_allow_html=True)
        st.markdown(f"**{user['name']}**")
        st.caption(f"{user['email']} · {user['role']}")
        if st.button("Sign out", width='stretch'):
            core.sign_out(user.get("access_token", ""))
            if ck is not None:
                try:
                    ck.remove(_COOKIE)
                except Exception:
                    pass
            del st.session_state.user
            st.rerun()
