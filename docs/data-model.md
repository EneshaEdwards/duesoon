# DueSoon Data Model

## Table: assignments

One row per assignment.

| Field | Type | Example | Notes |
|---|---|---|---|
| assignment_id (partition key) | string | "a1b2c3" | Unique ID generated when saved |
| title | string | "Chapter 5 essay" | What he types in the form |
| type | string | "homework" | homework, project, class_work or test |
| due_at | string (UTC, ISO format) | "2026-10-16T21:00:00Z" | Entered in Eastern time, stored in UTC |
| created_at | string (UTC, ISO format) | "2026-10-10T21:30:00Z" | When it was submitted |
| reminders_sent | list of strings | ["10d", "5d"] | Which reminders already went out |
| status | string | "active" | active or done |

## Reminder windows

10d, 5d, 3d, 1d, 12h before due_at.

## Decisions

- **Times are stored in UTC.** Eastern changes with daylight saving. The form converts to UTC when saving, and the emails convert back to Eastern.
- **reminders_sent prevents duplicates.** The hourly job sends a reminder only if its label is not in the list, then adds it.
- **Table scan.** The hourly job reads the whole table. That is fine for one student's assignments. An index on status and due_at is a later improvement.
- **On-demand billing.** Cost is near zero at this size.
- **No contact info in the table or the repo.** His email and phone are set outside GitHub.