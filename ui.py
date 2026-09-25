"""Shared Streamlit layer: brand, styling, Supabase login/sign-up, role guards.

Colors come from native Streamlit theming (.streamlit/config.toml, light + dark).
This module only adds brand bits and a few theme-aware tokens (--adr-*).
"""
from __future__ import annotations

import random
from datetime import date
from html import escape
from urllib.parse import urlparse

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

:root { --adr-accent:#A78BFA; --adr-muted:#A79FC7; --adr-ink:#EAE6F8;
        --adr-hair:rgba(167,139,250,.16); --adr-rule:rgba(234,230,248,.30);
        --adr-late:#F0857A; --adr-ease:cubic-bezier(.32,.72,0,1); }

/* Deep-space background: layered nebula glow + a fixed starfield behind everything.
   Kept subtle so starlight text stays fully legible (AA-validated). */
[data-testid="stApp"] {
  background-color:#0B0714;
  background-image:
    radial-gradient(1150px 780px at 12% -10%, rgba(124,77,255,.20), transparent 60%),
    radial-gradient(950px 700px at 110% 2%, rgba(168,85,247,.14), transparent 55%),
    radial-gradient(1000px 950px at 50% 120%, rgba(88,28,135,.22), transparent 62%),
    url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22340%22%20height%3D%22340%22%20viewBox%3D%220%200%20340%20340%22%3E%3Ccircle%20cx%3D%22217.4%22%20cy%3D%228.5%22%20r%3D%220.7%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.24%22%2F%3E%3Ccircle%20cx%3D%22250.4%22%20cy%3D%22230.1%22%20r%3D%221.0%22%20fill%3D%22%23cbb8ff%22%20opacity%3D%220.16%22%2F%3E%3Ccircle%20cx%3D%2210.8%22%20cy%3D%2231.9%22%20r%3D%220.6%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.36%22%2F%3E%3Ccircle%20cx%3D%22190.8%22%20cy%3D%22243.4%22%20r%3D%221.3%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.38%22%2F%3E%3Ccircle%20cx%3D%22152.7%22%20cy%3D%2294.6%22%20r%3D%220.5%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.48%22%2F%3E%3Ccircle%20cx%3D%22237.4%22%20cy%3D%22115.7%22%20r%3D%220.6%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.22%22%2F%3E%3Ccircle%20cx%3D%2234.8%22%20cy%3D%22129.2%22%20r%3D%220.7%22%20fill%3D%22%23b8c6ff%22%20opacity%3D%220.53%22%2F%3E%3Ccircle%20cx%3D%2289.9%22%20cy%3D%2214.8%22%20r%3D%220.8%22%20fill%3D%22%23cbb8ff%22%20opacity%3D%220.38%22%2F%3E%3Ccircle%20cx%3D%2226.8%22%20cy%3D%2299.7%22%20r%3D%221.3%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.42%22%2F%3E%3Ccircle%20cx%3D%22196.3%22%20cy%3D%22239.6%22%20r%3D%220.5%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.44%22%2F%3E%3Ccircle%20cx%3D%22335.0%22%20cy%3D%22290.8%22%20r%3D%220.5%22%20fill%3D%22%23cbb8ff%22%20opacity%3D%220.3%22%2F%3E%3Ccircle%20cx%3D%22216.1%22%20cy%3D%22124.0%22%20r%3D%220.7%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.29%22%2F%3E%3Ccircle%20cx%3D%22238.6%22%20cy%3D%22232.4%22%20r%3D%220.5%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.41%22%2F%3E%3Ccircle%20cx%3D%22181.6%22%20cy%3D%2283.2%22%20r%3D%220.8%22%20fill%3D%22%23b8c6ff%22%20opacity%3D%220.3%22%2F%3E%3Ccircle%20cx%3D%2274.7%22%20cy%3D%22110.3%22%20r%3D%220.5%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.23%22%2F%3E%3Ccircle%20cx%3D%22273.7%22%20cy%3D%22136.4%22%20r%3D%220.5%22%20fill%3D%22%23b8c6ff%22%20opacity%3D%220.22%22%2F%3E%3Ccircle%20cx%3D%22298.0%22%20cy%3D%22107.0%22%20r%3D%221.3%22%20fill%3D%22%23cbb8ff%22%20opacity%3D%220.36%22%2F%3E%3Ccircle%20cx%3D%2248.6%22%20cy%3D%2247.5%22%20r%3D%221.3%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.39%22%2F%3E%3Ccircle%20cx%3D%22254.0%22%20cy%3D%22145.7%22%20r%3D%221.0%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.31%22%2F%3E%3Ccircle%20cx%3D%22339.1%22%20cy%3D%2247.0%22%20r%3D%220.8%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.16%22%2F%3E%3Ccircle%20cx%3D%22292.8%22%20cy%3D%2252.0%22%20r%3D%220.6%22%20fill%3D%22%23cbb8ff%22%20opacity%3D%220.5%22%2F%3E%3Ccircle%20cx%3D%22202.8%22%20cy%3D%22130.8%22%20r%3D%221.0%22%20fill%3D%22%23b8c6ff%22%20opacity%3D%220.6%22%2F%3E%3Ccircle%20cx%3D%2285.5%22%20cy%3D%22188.1%22%20r%3D%220.5%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.45%22%2F%3E%3Ccircle%20cx%3D%22231.8%22%20cy%3D%22182.6%22%20r%3D%220.7%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.49%22%2F%3E%3Ccircle%20cx%3D%2237.9%22%20cy%3D%22147.8%22%20r%3D%220.8%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.12%22%2F%3E%3Ccircle%20cx%3D%22330.4%22%20cy%3D%22259.1%22%20r%3D%221.0%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.56%22%2F%3E%3Ccircle%20cx%3D%22286.2%22%20cy%3D%22172.6%22%20r%3D%220.6%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.19%22%2F%3E%3Ccircle%20cx%3D%22183.4%22%20cy%3D%22264.7%22%20r%3D%221.0%22%20fill%3D%22%23b8c6ff%22%20opacity%3D%220.56%22%2F%3E%3Ccircle%20cx%3D%22110.2%22%20cy%3D%226.6%22%20r%3D%220.7%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.54%22%2F%3E%3Ccircle%20cx%3D%2281.4%22%20cy%3D%2281.9%22%20r%3D%221.0%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.57%22%2F%3E%3Ccircle%20cx%3D%22248.8%22%20cy%3D%22277.4%22%20r%3D%221.0%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.49%22%2F%3E%3Ccircle%20cx%3D%22224.3%22%20cy%3D%22321.9%22%20r%3D%220.6%22%20fill%3D%22%23b8c6ff%22%20opacity%3D%220.25%22%2F%3E%3Ccircle%20cx%3D%22143.9%22%20cy%3D%2272.0%22%20r%3D%221.0%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.48%22%2F%3E%3Ccircle%20cx%3D%22242.4%22%20cy%3D%22135.7%22%20r%3D%221.3%22%20fill%3D%22%23cbb8ff%22%20opacity%3D%220.43%22%2F%3E%3Ccircle%20cx%3D%22305.9%22%20cy%3D%22153.5%22%20r%3D%220.6%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.23%22%2F%3E%3Ccircle%20cx%3D%227.2%22%20cy%3D%22188.3%22%20r%3D%221.0%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.23%22%2F%3E%3Ccircle%20cx%3D%22240.7%22%20cy%3D%2220.0%22%20r%3D%220.5%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.55%22%2F%3E%3Ccircle%20cx%3D%2224.1%22%20cy%3D%2280.9%22%20r%3D%221.3%22%20fill%3D%22%23b8c6ff%22%20opacity%3D%220.35%22%2F%3E%3Ccircle%20cx%3D%2245.0%22%20cy%3D%22318.1%22%20r%3D%221.0%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.4%22%2F%3E%3Ccircle%20cx%3D%22266.8%22%20cy%3D%22274.5%22%20r%3D%220.6%22%20fill%3D%22%23cbb8ff%22%20opacity%3D%220.17%22%2F%3E%3Ccircle%20cx%3D%22120.5%22%20cy%3D%22139.8%22%20r%3D%221.3%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.15%22%2F%3E%3Ccircle%20cx%3D%2220.6%22%20cy%3D%22247.6%22%20r%3D%220.5%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.24%22%2F%3E%3Ccircle%20cx%3D%22182.3%22%20cy%3D%2247.7%22%20r%3D%220.6%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.25%22%2F%3E%3Ccircle%20cx%3D%22297.3%22%20cy%3D%2225.6%22%20r%3D%221.0%22%20fill%3D%22%23b8c6ff%22%20opacity%3D%220.17%22%2F%3E%3Ccircle%20cx%3D%22284.2%22%20cy%3D%22329.5%22%20r%3D%220.6%22%20fill%3D%22%23cbb8ff%22%20opacity%3D%220.2%22%2F%3E%3Ccircle%20cx%3D%22163.7%22%20cy%3D%22294.0%22%20r%3D%220.5%22%20fill%3D%22%23ffffff%22%20opacity%3D%220.2%22%2F%3E%3C%2Fsvg%3E");
  background-repeat:no-repeat,no-repeat,no-repeat,repeat;
  background-size:auto,auto,auto,340px 340px;
  background-attachment:fixed;
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

/* Workspace: flat item rows (tasks, milestones, docs, update log) */
[class*="st-key-task_"], [class*="st-key-msrow_"], [class*="st-key-doc_"],
[class*="st-key-log_"] { border-top: 1px solid var(--adr-hair); padding: .55rem 1px .35rem; }
[class*="st-key-task_"] [data-testid="stExpander"] details,
[class*="st-key-log_"] [data-testid="stExpander"] details { border: 0; background: transparent; }
[class*="st-key-task_"] [data-testid="stExpander"] summary,
[class*="st-key-log_"] [data-testid="stExpander"] summary { padding: .2rem 0; min-height: 0; }
[class*="st-key-task_"] summary p, [class*="st-key-log_"] summary p {
  font-size: .78rem; color: var(--adr-muted); }
[class*="st-key-log_"] [data-testid="stExpander"] { margin-left: 6.4rem; }
@media (max-width: 640px) { [class*="st-key-log_"] [data-testid="stExpander"] { margin-left: 0; } }
.adr-item { padding-bottom: .9rem; }
.adr-item .t { font-weight: 500; }
.adr-item .s, .adr-item-due { font-size: .8rem; color: var(--adr-muted); }
.adr-item-due .due-r { display: inline; margin-left: .35rem; }

.adr-log { display: flex; gap: 1rem; padding-bottom: 1.1rem; }
.adr-log .when { flex: none; width: 5.4rem; font-size: .82rem; color: var(--adr-ink);
  font-weight: 500; padding-top: .1rem; }
.adr-log .when span { display: block; color: var(--adr-muted); font-weight: 400; font-size: .75rem; }
.adr-log .body { flex: 1; min-width: 0; }
.adr-log .head { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }
.adr-log .head b { font-weight: 600; }
.adr-log .note { margin-top: .35rem; white-space: pre-wrap; line-height: 1.55; }
.adr-log .by { margin-top: .3rem; font-size: .78rem; color: var(--adr-muted); }

.adr-doc { display: flex; align-items: baseline; gap: .8rem; text-decoration: none !important;
  color: var(--adr-ink) !important; }
.adr-doc .t { font-weight: 500; }
.adr-doc .s { font-size: .8rem; color: var(--adr-muted); }
.adr-doc:hover .t { color: var(--adr-accent); text-decoration: underline;
  text-underline-offset: 3px; }
.adr-doc .arrow { color: var(--adr-muted); transition: transform .22s var(--adr-ease); }
.adr-doc:hover .arrow { transform: translate(2px, -2px); color: var(--adr-accent); }

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

/* Subtle star twinkle: a fixed, non-interactive layer of stars gently pulsing at
   varied rates (so they don't blink in unison). Sits behind all content; the
   static starfield stays steady behind it. Disabled for reduced-motion. */
.adr-twinkle { position: fixed; inset: 0; z-index: -1; pointer-events: none; overflow: hidden; }
.adr-twinkle i { position: absolute; display: block; border-radius: 50%; background: #fff;
  box-shadow: 0 0 4px 1px rgba(199,184,255,.45); opacity: .3;
  animation: adr-tw var(--d,4s) var(--t,0s) ease-in-out infinite; will-change: opacity, transform; }
@keyframes adr-tw {
  0%, 100% { opacity: .12; transform: scale(.7); }
  50% { opacity: .85; transform: scale(1.12); }
}
@media (prefers-reduced-motion: reduce) { .adr-twinkle i { animation: none; opacity: .45; } }

/* Primary buttons: deep violet fill with white label (4.8:1, passes AA). */
[data-testid^="stBaseButton-primary"],
[data-testid^="stBaseButton-primary"] * { color: #fff !important; }
</style>
"""


def _twinkle_html(n: int = 32) -> str:
    """A fixed layer of stars that gently twinkle (seeded, so positions are stable)."""
    r = random.Random(7)
    stars = []
    for _ in range(n):
        stars.append(
            f'<i style="left:{round(r.uniform(1, 99), 1)}%;top:{round(r.uniform(1, 99), 1)}%;'
            f'width:{r.choice([1, 1, 1.5, 2])}px;height:{r.choice([1, 1, 1.5, 2])}px;'
            f'--d:{round(r.uniform(2.6, 6.0), 1)}s;--t:{round(r.uniform(0, 6), 1)}s"></i>')
    return '<div class="adr-twinkle" aria-hidden="true">' + "".join(stars) + "</div>"


_TWINKLE = _twinkle_html()


def apply_style() -> None:
    st.markdown(_STYLE, unsafe_allow_html=True)
    st.markdown(_TWINKLE, unsafe_allow_html=True)


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
    rel = ("" if done else "today" if n == 0 else "tomorrow" if n == 1
           else f"in {n}d" if n > 0 else f"{-n}d late")
    late = n < 0 and not done
    return (f'<span class="{"late" if late else ""}"><span class="due-d">{fmt_date(d)}'
            f'</span><span class="due-r">{rel}</span></span>')


def when(ts: str) -> str:
    """Timestamp → '10:12' today, else '21 Sep'."""
    d = as_date(ts)
    return ts[11:16] if d == date.today() else fmt_date(d)



# Chart accent: violet that holds >=3:1 (graphics) on the deep-space ground.
CLAY = "#A78BFA"

# streamlit-sortables renders in its own iframe; this restyles the Kanban board
# to match the cosmic theme (translucent columns, violet-lit cards).
BOARD_CSS = """
.sortable-component { display: flex; flex-direction: row; align-items: stretch;
  background: transparent; border: 0; padding: 0; gap: .8rem; }
.sortable-container { flex: 1; min-width: 0; margin: 0; background: rgba(167,139,250,.05);
  border: 1px solid rgba(167,139,250,.16); border-radius: 4px; padding: .4rem; }
.sortable-container-header { background: transparent; font: 600 .7rem Inter, system-ui,
  sans-serif; letter-spacing: .14em; text-transform: uppercase; color: #A79FC7;
  padding: .35rem .4rem .5rem; }
.sortable-container-body { display: flex; flex-direction: column; background: transparent;
  min-height: 3rem; }
.sortable-item, .sortable-item:hover { background: #1B1533; color: #EAE6F8;
  border: 1px solid rgba(167,139,250,.18); border-radius: 3px; font: 500 .85rem Inter,
  system-ui, sans-serif; padding: .5rem .6rem; margin: 0 0 .35rem; box-shadow: none;
  text-align: left; justify-content: flex-start; }
.sortable-item:hover { border-color: #A78BFA; }
"""


def _safe_url(url: str) -> str:
    return url if str(url).lower().startswith(("http://", "https://")) else "#"


def link(label: str, url: str) -> str:
    return (f'<a href="{escape(_safe_url(url))}" target="_blank" rel="noopener">'
            f'{escape(label or url)}</a>')


def doc_row(label: str, url: str) -> str:
    host = urlparse(url).netloc.removeprefix("www.") or url
    return (f'<a class="adr-doc" href="{escape(_safe_url(url))}" target="_blank" '
            f'rel="noopener"><span class="t">{escape(label or host)}</span>'
            + (f'<span class="s">{escape(host)}</span>' if label else "")
            + '<span class="arrow">↗</span></a>')


def log_entry(ts: str, pill: str, title: str, note: str, author: str) -> str:
    """One dated entry in a project's update log (lab-notebook style)."""
    return (f'<div class="adr-log"><div class="when">{fmt_date(ts)}'
            f'<span>{escape(ts[11:16])}</span></div><div class="body">'
            f'<div class="head">{pill}<b>{escape(title)}</b></div>'
            + (f'<div class="note">{escape(note)}</div>' if note else "")
            + f'<div class="by">{escape(author)}</div></div></div>')


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
