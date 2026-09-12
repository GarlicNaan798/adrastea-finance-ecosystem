"""Live end-to-end check against your Supabase Postgres. Self-cleaning.

Prereqs: schema.sql applied, and at least one account signed up.
Run (PowerShell):  $env:DATABASE_URL="postgresql://..."; py tests/smoke_live.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core  # noqa: E402

if not core._secret("DATABASE_URL"):
    sys.exit("Set DATABASE_URL (and run schema.sql first).")

profs = core.list_profiles()
if not profs:
    sys.exit("Sign up at least one account in the app before running this.")
uid = profs[0]["id"]

pid = core.create_proposal("SMOKE TEST — delete me", uid, "smoke", "2026")
core.set_budget_lines(pid, [
    {"category": "Equipment", "description": "sensors", "amount": 1000},
    {"category": "Travel", "description": "fieldwork", "amount": 500.50},
    {"category": "Other", "description": "", "amount": 0},  # dropped
])
assert core.get_proposal(pid)["requested_amount"] == 1500.50
assert len(core.list_budget_lines(pid)) == 2

core.submit_proposal(pid)
core.decide_proposal(pid, True, uid, "smoke")
proj = core.get_proposal(pid)["project_id"]
assert proj, "approval should create a project"

t1 = core.create_transaction("2026-02-01", "expense", proj, "Equipment", "a", 300, uid)
t2 = core.create_transaction("2026-02-02", "expense", proj, "Equipment", "b", 250, uid)

bva = {r["category"]: r for r in core.budget_vs_actual(proj)}
assert bva["Equipment"]["budget"] == 1000
assert bva["Equipment"]["spent"] == 550
assert bva["Equipment"]["remaining"] == 450
assert bva["Travel"]["remaining"] == 500.50

# cleanup
core._run("DELETE FROM transactions WHERE id IN (%s,%s)", (t1, t2))
core._run("DELETE FROM budget_lines WHERE proposal_id = %s", (pid,))
core._run("DELETE FROM proposals WHERE id = %s", (pid,))
core._run("DELETE FROM projects WHERE id = %s", (proj,))
print("live smoke passed — budget-vs-actual correct, test rows cleaned up.")
