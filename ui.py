"""Shared Streamlit layer: brand, styling, Supabase login/sign-up, role guards.

Colors come from native Streamlit theming (.streamlit/config.toml, light + dark).
This module only adds brand bits and a few theme-aware tokens (--adr-*).
"""
from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st
from streamlit_cookies_controller import CookieController

import core

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


def _cookie_value(ck):
    """Read our cookie. st.context.cookies is synchronous (from the request
    headers) so it's there on the very FIRST run after a refresh / new tab — the
    cookie *component* (ck.get) returns nothing until it mounts, which is what made
    the app sign you out on every refresh. Component is only a fallback here."""
    try:
        rt = st.context.cookies.get(_COOKIE)
        if rt:
            return rt
    except Exception:
        pass
    if ck is not None:
        try:
            return ck.get(_COOKIE)
        except Exception:
            pass
    return None


def _restore_session(ck) -> dict | None:
    """Rebuild the user from the refresh-token cookie, if present and valid."""
    rt = _cookie_value(ck)
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
        --adr-hair:rgba(35,33,28,.10); --adr-rule:rgba(35,33,28,.55);
        --adr-late:#9B3D33; --adr-ease:cubic-bezier(.32,.72,0,1); }
@media (prefers-color-scheme: dark) {
  :root { --adr-accent:#C08A63; --adr-muted:#A79E90; --adr-ink:#ECE7DD;
          --adr-hair:rgba(255,255,255,.10); --adr-rule:rgba(236,231,221,.45);
          --adr-late:#E08A7E; }
}

.block-container { max-width: 1500px; padding: 2.4rem 2.6rem 4rem; }
@media (max-width: 768px) { .block-container { padding: 1.4rem 1rem 3rem; } }

/* Hide Streamlit chrome for a cleaner, app-like surface */
#MainMenu, [data-testid="stToolbar"], [data-testid="stDecoration"],
.stDeployButton, footer { display: none !important; }
[data-testid="stHeader"] { background: transparent; }

/* Type: Fraunces for display, tight and optical; numbers always tabular */
h1, h2, h3, h4 { font-family: 'Fraunces', Georgia, serif !important;
  font-optical-sizing: auto; letter-spacing: -.012em; }
h1 { font-weight: 500 !important; font-size: 2.5rem !important; line-height: 1.1 !important; }
h4 { font-weight: 500 !important; }
[data-testid="stMain"] { font-variant-numeric: tabular-nums; }

/* Page enters once on navigation — a short settle, nothing theatrical */
[data-testid="stMainBlockContainer"] > div { animation: adr-in .42s var(--adr-ease) both; }
@keyframes adr-in { from { opacity: 0; transform: translateY(6px); } }
@media (prefers-reduced-motion: reduce) {
  [data-testid="stMainBlockContainer"] > div { animation: none; }
}

/* Quiet, flat metrics (budget total etc.) */
[data-testid="stMetric"] { background: transparent; padding: 0; }
[data-testid="stMetricLabel"] p { text-transform: uppercase; letter-spacing: .1em;
  font-size: .7rem; color: var(--adr-muted); }
[data-testid="stMetricValue"] { font-family: 'Fraunces', Georgia, serif; font-weight: 500; }

/* Accessible muted text */
.meta { color: var(--adr-muted); }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--adr-muted); }

/* Page header: clay eyebrow, serif title, muted dateline */
.overline { font-size: .7rem; letter-spacing: .22em; text-transform: uppercase;
  color: var(--adr-accent); font-weight: 600; margin: 0 0 .35rem 1px; }
.dateline { color: var(--adr-muted); font-size: .9rem; margin: -.4rem 0 1.6rem 1px; }

/* Readout: an instrument strip, not a row of cards */
.adr-readout { display: grid; grid-auto-flow: column; grid-auto-columns: 1fr;
  border-top: 1px solid var(--adr-rule); border-bottom: 1px solid var(--adr-hair);
  margin: 0 0 2.4rem; }
.adr-readout .cell { padding: .8rem 1.1rem .9rem; border-left: 1px solid var(--adr-hair); }
.adr-readout .cell:first-child { border-left: 0; padding-left: 1px; }
.adr-readout .k { font-size: .68rem; letter-spacing: .14em; text-transform: uppercase;
  color: var(--adr-muted); font-weight: 500; }
.adr-readout .v { font-family: 'Fraunces', Georgia, serif; font-size: 2.1rem;
  font-weight: 400; line-height: 1.15; margin-top: .2rem; color: var(--adr-ink); }
.adr-readout .v.alert { color: var(--adr-late); }
@media (max-width: 640px) {
  .adr-readout { grid-auto-flow: row; grid-template-columns: 1fr 1fr; }
  .adr-readout .cell:nth-child(odd) { border-left: 0; padding-left: 1px; }
  .adr-readout .cell:nth-child(n+3) { border-top: 1px solid var(--adr-hair); }
}

/* Section: a printed-report rule, small-caps label, count */
.adr-section { display: flex; align-items: baseline; gap: .6rem;
  border-top: 1px solid var(--adr-rule); padding: .7rem 1px .55rem;
  font-size: .72rem; letter-spacing: .14em; text-transform: uppercase;
  font-weight: 600; color: var(--adr-ink); }
.adr-section .n { color: var(--adr-muted); font-weight: 500; letter-spacing: .04em; }
.adr-section .note { margin-left: auto; color: var(--adr-muted); font-weight: 400;
  letter-spacing: 0; text-transform: none; font-size: .8rem; }
.adr-empty { color: var(--adr-muted); font-size: .9rem; padding: .7rem 1px;
  border-top: 1px solid var(--adr-hair); }

/* List rows: the visual is HTML; an invisible button covers the whole row, so the
   entire row is one click / keyboard target (file-browser feel, no borders). */
[class*="st-key-row_"] { position: relative; gap: 0 !important; }
[class*="st-key-rowbtn_"] { position: absolute !important; inset: 0; z-index: 1; margin: 0;
  width: 100% !important; height: 100% !important; }
[class*="st-key-rowbtn_"] * { position: static !important; }
[class*="st-key-rowbtn_"] button { position: absolute !important; inset: 0;
  width: 100%; height: 100%; opacity: 0; cursor: pointer; }
.adr-row { display: flex; align-items: center; gap: 1rem; min-height: 3.1rem;
  padding: .55rem .7rem; border-top: 1px solid var(--adr-hair);
  transition: background-color .22s var(--adr-ease), box-shadow .22s var(--adr-ease); }
.adr-row .lead { flex: none; width: 6.4rem; }
.adr-row .body { flex: 1; min-width: 0; }
.adr-row .t { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.adr-row .s { font-size: .8rem; color: var(--adr-muted); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; margin-top: .05rem; }
.adr-row .aside { flex: none; text-align: right; font-size: .82rem; color: var(--adr-muted);
  max-width: 45%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
[class*="st-key-row_"]:hover .adr-row {
  background: color-mix(in srgb, var(--adr-accent) 6%, transparent);
  box-shadow: inset 2px 0 0 var(--adr-accent); }
[class*="st-key-row_"]:has(button:focus-visible) .adr-row {
  outline: 2px solid var(--adr-accent); outline-offset: -2px; }

@media (max-width: 640px) { .wide-only { display: none; } }

.due-d { color: var(--adr-ink); font-weight: 500; }
.due-r { display: block; font-size: .72rem; color: var(--adr-muted); }
.late, .late .due-d, .late .due-r { color: var(--adr-late); }

/* Status: solid colour, white text, near-square corners (print, not app-store) */
.adr-pill { display: inline-block; color: #fff; border-radius: 3px; padding: .16rem .5rem;
  font-size: .7rem; font-weight: 600; letter-spacing: .02em; white-space: nowrap;
  line-height: 1.35; }
.adr-tag { display: inline-block; border: 1px solid var(--adr-hair); border-radius: 3px;
  padding: .1rem .45rem; font-size: .7rem; font-weight: 500; color: var(--adr-muted);
  white-space: nowrap; }
.adr-tag.doing { color: var(--adr-ink); border-color: var(--adr-rule); }

/* Sidebar: brand + who-you-are on top, nav below, hairline edge */
[data-testid="stSidebar"] { border-right: 1px solid var(--adr-hair); }
[data-testid="stSidebarContent"] { display: flex; flex-direction: column; }
[data-testid="stSidebarHeader"] { order: -2; }
[data-testid="stSidebarUserContent"] { order: -1; padding-bottom: .4rem; }
.brandbar { display: flex; align-items: center; gap: .55rem; padding: 0 0 .9rem;
  color: var(--adr-ink); }
.brandbar .name { font-family: 'Fraunces', Georgia, serif; font-size: 1.4rem;
  font-weight: 600; letter-spacing: -.01em; }
.whoami { font-size: .82rem; line-height: 1.4; }
.whoami b { font-weight: 600; }
[data-testid="stSidebarNav"] a { border-radius: 4px;
  transition: background-color .2s var(--adr-ease); }
[data-testid="stSidebarNav"] a[aria-current="page"] span { color: var(--adr-accent); font-weight: 600; }

/* Tabs, expanders, rules */
.stTabs [data-baseweb="tab-list"] { gap: 1.8rem; border-bottom: 1px solid var(--adr-hair); }
.stTabs [data-baseweb="tab"] p { font-weight: 500; }
[data-testid="stExpander"] details { border-radius: 4px; border-color: var(--adr-hair); }
hr { margin: 1.2rem 0; opacity: .6; }
button { transition: background-color .2s var(--adr-ease), border-color .2s var(--adr-ease),
  transform .2s var(--adr-ease) !important; }
button:active { transform: scale(.985); }

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


def page_header(title: str, overline: str | None = None, dateline: str | None = None) -> None:
    if overline:
        st.markdown(f'<div class="overline">{escape(overline)}</div>', unsafe_allow_html=True)
    st.markdown(f"# {title}")
    if dateline:
        st.markdown(f'<div class="dateline">{escape(dateline)}</div>', unsafe_allow_html=True)


# Solid pills with white text — pass WCAG AA in both light and dark.
_STATUS_COLORS = {"on_track": "#2F6B4F", "at_risk": "#8A5A1E",
                  "blocked": "#9B3D33", "done": "#3A4A5E"}


def status_pill(status: str) -> str:
    label = core.PROGRESS_LABELS.get(status, status)
    c = _STATUS_COLORS.get(status, "#555")
    return f'<span class="adr-pill" style="background:{c}">{escape(label)}</span>'


def task_tag(status: str) -> str:
    """Task state is neutral (outline) so colour stays reserved for project health."""
    return (f'<span class="adr-tag {escape(status)}">'
            f'{escape(core.TASK_LABELS.get(status, status))}</span>')


def as_date(iso) -> date | None:
    try:
        return date.fromisoformat(str(iso)[:10]) if iso else None
    except ValueError:
        return None


def fmt_date(iso) -> str:
    """'29 Sep' this year, '29 Sep 2027' otherwise, '—' when missing."""
    d = as_date(iso)
    if not d:
        return "—"
    return f"{d.day} {d:%b}" + ("" if d.year == date.today().year else f" {d.year}")


def due(iso, done: bool = False) -> str:
    """Due date plus a relative hint ('in 6d', 'today', '3d late'); late turns red."""
    d = as_date(iso)
    if not d:
        return '<span class="due-r">no date</span>'
    n = (d - date.today()).days
    rel = "today" if n == 0 else "tomorrow" if n == 1 else f"in {n}d" if n > 0 else f"{-n}d late"
    late = n < 0 and not done
    return (f'<span class="{"late" if late else ""}"><span class="due-d">{fmt_date(d)}'
            f'</span><span class="due-r">{rel}</span></span>')


def when(ts: str) -> str:
    """Timestamp → '10:12' today, else '21 Sep'."""
    d = as_date(ts)
    return ts[11:16] if d == date.today() else fmt_date(d)


def readout(cells: list[tuple[str, int | str, bool]]) -> None:
    """Instrument-style stat strip. cells = (label, value, alert)."""
    html = "".join(f'<div class="cell"><div class="k">{escape(k)}</div>'
                   f'<div class="v{" alert" if alert else ""}">{escape(str(v))}</div></div>'
                   for k, v, alert in cells)
    st.markdown(f'<div class="adr-readout">{html}</div>', unsafe_allow_html=True)


def section(label: str, count: int | None = None, note: str = "") -> None:
    n = f'<span class="n">{count}</span>' if count is not None else ""
    note = f'<span class="note">{escape(note)}</span>' if note else ""
    st.markdown(f'<div class="adr-section"><span>{escape(label)}</span>{n}{note}</div>',
                unsafe_allow_html=True)


def empty(text: str) -> None:
    st.markdown(f'<div class="adr-empty">{escape(text)}</div>', unsafe_allow_html=True)


def row(key: str, title: str, sub: str = "", lead: str = "", aside: str = "") -> bool:
    """Full-width clickable list row. `title`/`sub` are plain text (escaped here);
    `lead`/`aside` are HTML from the helpers above. Returns True when clicked."""
    html = (f'<div class="adr-row">'
            + (f'<div class="lead">{lead}</div>' if lead else "")
            + f'<div class="body"><div class="t">{escape(title)}</div>'
            + (f'<div class="s">{escape(sub)}</div>' if sub else "") + '</div>'
            + (f'<div class="aside">{aside}</div>' if aside else "") + '</div>')
    with st.container(key=f"row_{key}", gap=None):
        st.markdown(html, unsafe_allow_html=True)
        return st.button(title, key=f"rowbtn_{key}")


def open_project(pid) -> None:
    st.session_state.open_project = pid
    st.switch_page(st.session_state["_pages"]["projects"])


def comment_thread(parent_type: str, parent_id: int, user: dict,
                   can_comment: bool, key_suffix: str = "") -> None:
    """Collapsible comment thread under a discussion update or a task.
    key_suffix disambiguates when the same item renders in two places."""
    comments = core.list_comments(parent_type, parent_id)
    with st.expander(f"Comments ({len(comments)})"):
        for c in comments:
            when = c["created_at"][:16].replace("T", " ")
            st.markdown(f'**{escape(c["author_name"] or "—")}** '
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
        st.markdown(
            f'<div class="whoami"><b>{escape(user["name"])}</b><br>'
            f'<span class="meta">{escape(core.ROLE_LABELS.get(user["role"], user["role"]))}'
            f' · {escape(user["email"])}</span></div>', unsafe_allow_html=True)
        if st.button("Sign out", type="tertiary", icon=":material/logout:"):
            core.sign_out(user.get("access_token", ""))
            if ck is not None:
                try:
                    ck.remove(_COOKIE)
                except Exception:
                    pass
            del st.session_state.user
            st.rerun()
