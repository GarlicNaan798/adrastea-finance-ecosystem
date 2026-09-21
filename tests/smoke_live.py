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
TRACK = "CHASM Project"

pid = core.create_project("SMOKE TEST — delete me", "desc", "needs X and Y",
                          "active", TRACK, uid)
try:
    # track director + team round-trip
    core.set_track_director(TRACK, uid)
    assert TRACK in core.owned_tracks(uid)
    core.add_track_member(TRACK, uid, is_lead=True)
    assert TRACK in core.member_tracks(uid) and TRACK in core.lead_tracks(uid)
    assert core.can_edit_project(False, TRACK in core.owned_tracks(uid),
                                 TRACK in core.lead_tracks(uid))

    core.set_budget_lines(pid, [
        {"category": "Equipment", "description": "sensors", "amount": 1000},
        {"category": "Travel", "description": "fieldwork", "amount": 500.50},
        {"category": "Other", "description": "", "amount": 0}])   # dropped
    assert core.project_budget_total(pid) == 1500.50
    assert len(core.list_budget_lines(pid)) == 2

    # discussion updates (title + timestamp, newest first)
    core.add_progress(pid, uid, "Kickoff", "at_risk", "waiting on parts")
    core.add_progress(pid, uid, "Parts in", "on_track", "assembling")
    feed = core.list_progress(project_id=pid)
    assert len(feed) == 2 and feed[0]["title"] == "Parts in"          # newest first
    latest = {r["project_id"]: r for r in core.latest_progress_by_project()}
    assert latest[pid]["status"] == "on_track"

    # tasks
    tid = core.create_task(pid, "Wire the array", "carefully", uid, "2026-10-01", uid)
    assert core.list_tasks(assignee_id=uid)[0]["status"] == "todo"
    core.set_task_status(tid, "done")
    assert core.list_tasks(project_id=pid)[0]["status"] == "done"

    print("live smoke passed — project, team, budget, discussion, tasks reconcile.")
finally:
    core.set_track_director(TRACK, None)
    core.remove_track_member(TRACK, uid)
    core.delete_project(pid)  # cascades budget_lines, updates, tasks, links
    assert core.get_project(pid) is None
    print("cleaned up.")
