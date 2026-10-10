from datetime import datetime, timedelta, timezone

from reminder import build_message, reminders_due

NOW = datetime(2026, 10, 10, 22, 0, 0, tzinfo=timezone.utc)


def item(hours_left, sent=None):
    due = NOW + timedelta(hours=hours_left)
    return {
        "assignment_id": "x",
        "title": "Chinese test",
        "type": "test",
        "due_at": due.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reminders_sent": sent or [],
    }


def check(name, got, want):
    status = "PASS" if got == want else "FAIL"
    print(f"{status}  {name}: {got}")
    assert got == want


check("11 days left -> nothing", reminders_due(item(11 * 24), NOW), None)
check("just under 10 days -> send 10d", reminders_due(item(10 * 24 - 1), NOW), ("10d", ["10d"]))
check("4 days, nothing sent -> ONE email, mark 10d+5d", reminders_due(item(4 * 24), NOW), ("5d", ["5d", "10d"]))
check("4 days, 10d+5d already sent -> nothing", reminders_due(item(4 * 24, ["10d", "5d"]), NOW), None)
check("2.5 days, 10d+5d sent -> send 3d", reminders_due(item(60, ["10d", "5d"]), NOW), ("3d", ["3d"]))
check("30 hours, nothing sent -> send 3d, mark 3d/5d/10d", reminders_due(item(30), NOW), ("3d", ["3d", "5d", "10d"]))
check("20 hours -> send 1d", reminders_due(item(20, ["10d", "5d", "3d"]), NOW), ("1d", ["1d"]))
check("5 hours -> send 12h", reminders_due(item(5, ["10d", "5d", "3d", "1d"]), NOW), ("12h", ["12h"]))
check("everything sent -> nothing", reminders_due(item(5, ["10d", "5d", "3d", "1d", "12h"]), NOW), None)
check("past due -> nothing", reminders_due(item(-1), NOW), None)
check("late add, 5h, nothing sent -> ONE email", reminders_due(item(5), NOW), ("12h", ["12h", "1d", "3d", "5d", "10d"]))

subject, body = build_message(item(30), NOW)
print(subject)
print(body)
assert subject == "Test due in 1 day: Chinese test"
print("All tests passed")