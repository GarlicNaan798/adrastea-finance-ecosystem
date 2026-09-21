"""Live end-to-end check against your Supabase Postgres. Self-cleaning.

Prereqs: schema.sql applied, and at least one account signed up.
Run (PowerShell):  py tests/smoke_live.py
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

pid = core.create_project("SMOKE TEST — delete me", "desc",
                          "needs X and Y", "active", "CHASM Project", uid)
# track leads + coordinator round-trip
core.assign_track_lead("CHASM Project", uid)
assert "CHASM Project" in core.lead_tracks(uid)
assert core.can_edit_project_role("member", "CHASM Project" in core.lead_tracks(uid))
core.set_track_coordinator("CHASM Project", uid)
assert core.track_coordinators().get("CHASM Project", {}).get("user_id") == uid
core.set_track_coordinator("CHASM Project", None)
core.remove_track_lead("CHASM Project", uid)
assert "CHASM Project" not in core.lead_tracks(uid)
core.set_budget_lines(pid, [
    {"category": "Equipment", "description": "sensors", "amount": 1000},
    {"category": "Travel", "description": "fieldwork", "amount": 500.50},
    {"category": "Other", "description": "", "amount": 0},  # dropped (blank+0)
])
assert core.project_budget_total(pid) == 1500.50
assert len(core.list_budget_lines(pid)) == 2

wk = core.week_monday()
core.add_progress(pid, uid, "at_risk", "waiting on parts", wk)
core.add_progress(pid, uid, "on_track", "parts arrived", wk)

feed = core.list_progress(project_id=pid)
assert len(feed) == 2
assert feed[0]["project_name"] == "SMOKE TEST — delete me"
assert {f["status"] for f in feed} == {"at_risk", "on_track"}

latest = {r["project_id"]: r for r in core.latest_progress_by_project()}
assert pid in latest and latest[pid]["status"] == "on_track"  # most recent

core.delete_project(pid)  # cascades budget_lines + progress_updates
assert core.get_project(pid) is None
print("live smoke passed — project, budget, progress all reconcile; cleaned up.")
