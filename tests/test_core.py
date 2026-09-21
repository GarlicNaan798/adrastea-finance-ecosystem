"""Offline self-checks (no DB needed). Run: py tests/test_core.py

The DB-backed flow is verified live against Supabase (tests/smoke_live.py).
"""
import os
import sys
from datetime import date

os.environ.setdefault("SUPABASE_URL", "https://demo.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-key")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core  # noqa: E402


def test_money_formatting():
    assert core.money(0) == "$0.00"
    assert core.money(1500.5) == "$1,500.50"
    assert core.money(None) == "$0.00"
    assert core.money(1234567.891) == "$1,234,567.89"


def test_auth_url_and_headers():
    assert core._auth_url("token") == "https://demo.supabase.co/auth/v1/token"
    h = core._auth_headers("abc")
    assert h["apikey"] == "anon-key"
    assert h["Authorization"] == "Bearer abc"
    assert "Authorization" not in core._auth_headers()


def test_allowlists_and_roles():
    os.environ["DIRECTOR_EMAILS"] = "Alice@x.org, bob@x.org"
    os.environ["FOUNDER_EMAILS"] = "carol@x.org"
    assert core.director_emails() == {"alice@x.org", "bob@x.org"}
    assert core.founder_emails() == {"carol@x.org"}
    assert core.role_for_email("BOB@x.org") == "director"
    assert core.role_for_email("carol@x.org") == "founder"
    assert core.role_for_email("dave@x.org") == "member"
    os.environ["DIRECTOR_EMAILS"] = "carol@x.org"          # founder wins if in both
    assert core.role_for_email("carol@x.org") == "founder"
    del os.environ["DIRECTOR_EMAILS"]
    del os.environ["FOUNDER_EMAILS"]


def test_roles():
    assert core.ROLES == ("member", "director", "founder")


def test_tracks():
    assert "CHASM Project" in core.TRACKS
    assert len(core.TRACKS) == 5
    assert "Bioengineering & Tech" in core.TRACKS


def test_permissions():
    assert core.can_manage_track(True, False) is True    # founder anywhere
    assert core.can_manage_track(False, True) is True     # the track's director
    assert core.can_manage_track(False, False) is False
    assert core.can_edit_project(False, True, False) is True   # track director
    assert core.can_edit_project(False, False, True) is True   # lead
    assert core.can_edit_project(False, False, False) is False
    assert core.can_post_update(False, False, True) is True    # team member
    assert core.can_post_update(False, False, False) is False


def test_clean_url():
    assert core.clean_url("https://drive.google.com/x") == "https://drive.google.com/x"
    assert core.clean_url("http://x.org") == "http://x.org"
    assert core.clean_url("  https://x.org/y  ") == "https://x.org/y"
    assert core.clean_url("javascript:alert(1)") is None  # XSS guard
    assert core.clean_url("ftp://x.org/f") is None
    assert core.clean_url("not a url") is None
    assert core.clean_url("") is None


def test_redirect_suffix():
    os.environ["APP_URL"] = "https://adrastea.streamlit.app/"
    assert core._redirect_suffix() == \
        "?redirect_to=https%3A%2F%2Fadrastea.streamlit.app%2F"
    del os.environ["APP_URL"]


def test_week_monday():
    wm = core.week_monday(date(2026, 9, 16))  # a Wednesday
    d = date.fromisoformat(wm)
    assert d.weekday() == 0            # it's a Monday
    assert 0 <= (date(2026, 9, 16) - d).days <= 6


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all passed")
