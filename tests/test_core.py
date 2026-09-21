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


def test_director_allowlist():
    os.environ["DIRECTOR_EMAILS"] = "Alice@x.org, bob@x.org ; carol@x.org"
    assert core.director_emails() == {"alice@x.org", "bob@x.org", "carol@x.org"}
    assert core.role_for_email("BOB@x.org") == "director"
    assert core.role_for_email("  Alice@x.org ") == "director"
    assert core.role_for_email("dave@x.org") == "member"
    assert core.role_for_email("") == "member"


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
