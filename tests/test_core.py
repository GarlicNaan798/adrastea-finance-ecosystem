"""Offline self-checks (no DB needed). Run: py tests/test_core.py

The budget/finance SQL is verified live against Supabase during setup
(tests/smoke_live.py).
"""
import os
import sys

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


def test_role_sets():
    assert "pending" in core.ALL_ROLES
    assert "pending" not in core.ASSIGNABLE_ROLES
    assert set(core.ASSIGNABLE_ROLES) < set(core.ALL_ROLES)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all passed")
