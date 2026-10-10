import base64
import hmac
import os
import uuid
from datetime import datetime, timezone
from html import escape
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

import boto3

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
PASSCODE = os.environ["PASSCODE"]
EASTERN = ZoneInfo("America/New_York")

TYPES = {
    "homework": "Homework",
    "project": "Project",
    "class_work": "Class work",
    "test": "Test",
}


def build_page(message="", ok=False):
    options = "".join(
        f'<option value="{value}">{label}</option>' for value, label in TYPES.items()
    )
    note = ""
    if message:
        color = "#1a7f37" if ok else "#c62828"
        note = f'<p style="color:{color};font-weight:bold">{escape(message)}</p>'
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DueSoon</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 420px; margin: 24px auto; padding: 0 16px; }}
  label {{ display: block; margin-top: 14px; font-weight: bold; }}
  input, select, button {{ width: 100%; padding: 12px; font-size: 16px; margin-top: 6px; box-sizing: border-box; }}
  button {{ margin-top: 22px; background: #2563eb; color: white; border: 0; border-radius: 8px; }}
</style>
</head>
<body>
<h1>DueSoon</h1>
{note}
<form method="post">
  <label>What is it?</label>
  <input name="title" maxlength="100" required>
  <label>Type</label>
  <select name="type">{options}</select>
  <label>Due date</label>
  <input type="date" name="due_date" required>
  <label>Due time</label>
  <input type="time" name="due_time" required>
  <label>Passcode</label>
  <input type="password" name="passcode" required>
  <button type="submit">Save</button>
</form>
</body>
</html>"""


def respond(body, status=200):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": body,
    }


def read_form(event):
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    return {key: values[0] for key, values in parse_qs(body).items()}


def handle_post(event):
    form = read_form(event)

    given = form.get("passcode", "").encode()
    if not hmac.compare_digest(given, PASSCODE.encode()):
        return respond(build_page("Wrong passcode."), 403)

    title = form.get("title", "").strip()
    if not title or len(title) > 100:
        return respond(build_page("Add a name for the assignment."), 400)

    assignment_type = form.get("type", "")
    if assignment_type not in TYPES:
        return respond(build_page("Pick a type."), 400)

    try:
        due_local = datetime.strptime(
            f"{form.get('due_date', '')} {form.get('due_time', '')}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=EASTERN)
    except ValueError:
        return respond(build_page("Check the date and time."), 400)

    due_utc = due_local.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if due_utc <= now:
        return respond(build_page("That time has already passed."), 400)

    TABLE.put_item(
        Item={
            "assignment_id": uuid.uuid4().hex,
            "title": title,
            "type": assignment_type,
            "due_at": due_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reminders_sent": [],
            "status": "active",
        }
    )
    return respond(build_page(f"Saved: {title}", ok=True))


def lambda_handler(event, context):
    method = event["requestContext"]["http"]["method"]
    if method == "GET":
        return respond(build_page())
    if method == "POST":
        return handle_post(event)
    return respond(build_page("Not allowed."), 405)