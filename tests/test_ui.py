from datetime import date, timedelta

import ui


def test_date_helpers():
    t = date.today()
    iso = lambda n: (t + timedelta(days=n)).isoformat()
    assert ui.fmt_date(None) == "—" and ui.fmt_date("junk") == "—"
    assert ui.fmt_date(f"{t.year + 1}-03-05") == f"5 Mar {t.year + 1}"
    assert "today" in ui.due(iso(0)) and "tomorrow" in ui.due(iso(1))
    assert "in 6d" in ui.due(iso(6)) and "late" not in ui.due(iso(6))
    assert "3d late" in ui.due(iso(-3)) and 'class="late"' in ui.due(iso(-3))
    assert 'class="late"' not in ui.due(iso(-3), done=True)
    assert "late" not in ui.due(iso(-3), done=True)
    assert "no date" in ui.due(None)
    assert ui.when(f"{t.isoformat()}T10:12:00+00:00") == "10:12"


def test_row_text_is_escaped():
    assert "&lt;img" in ui.status_pill("<img src=x onerror=alert(1)>")
