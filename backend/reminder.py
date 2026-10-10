import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")

# Smallest window first, so the most urgent matching window is easy to pick.
WINDOWS = [
    ("12h", timedelta(hours=12)),
    ("1d", timedelta(days=1)),
    ("3d", timedelta(days=3)),
    ("5d", timedelta(days=5)),
    ("10d", timedelta(days=10)),
]

TYPE_LABELS = {
    "homework": "Homework",
    "project": "Project",
    "class_work": "Class work",
    "test": "Test",
}


def parse_utc(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def reminders_due(assignment, now):
    """Return (label_to_send, labels_to_mark) or None.

    A window is reached once the time left is at or under it. If several
    windows are reached at once (an assignment added late), we send ONE email
    for the most urgent window and mark all the reached windows as sent.
    """
    time_left = parse_utc(assignment["due_at"]) - now
    if time_left <= timedelta(0):
        return None

    already_sent = set(assignment.get("reminders_sent", []))
    reached = [label for label, size in WINDOWS if time_left <= size]
    new = [label for label in reached if label not in already_sent]
    if not new:
        return None

    most_urgent = reached[0]
    to_send = most_urgent if most_urgent in new else None
    return to_send, new


def time_left_text(due_at, now):
    seconds = (parse_utc(due_at) - now).total_seconds()
    hours = int(seconds // 3600)
    if hours >= 48:
        return f"{hours // 24} days"
    if hours >= 24:
        return "1 day"
    if hours >= 2:
        return f"{hours} hours"
    if hours == 1:
        return "1 hour"
    return "less than an hour"


def build_message(assignment, now):
    due_local = parse_utc(assignment["due_at"]).astimezone(EASTERN)
    kind = TYPE_LABELS.get(assignment["type"], assignment["type"])
    left = time_left_text(assignment["due_at"], now)
    subject = f"{kind} due in {left}: {assignment['title']}"
    body = (
        f"{assignment['title']} ({kind}) is due in {left}.\n\n"
        f"Due: {due_local.strftime('%A, %B %-d at %-I:%M %p')} Eastern\n"
    )
    return subject, body


def send_push(topic, title, message, urgent):
    """Send a push notification through ntfy. Never raises: email is the main channel."""
    if not topic:
        return
    payload = {
        "topic": topic,
        "title": title,
        "message": message,
        "priority": 4 if urgent else 3,
        "tags": ["alarm_clock"],
    }
    request = urllib.request.Request(
        "https://ntfy.sh/",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=10).close()
    except Exception as error:
        print(f"Push failed: {error}")


def lambda_handler(event, context):
    import boto3
    from boto3.dynamodb.conditions import Attr

    table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    ses = boto3.client("sesv2")
    sender = os.environ["SENDER"]
    recipient = os.environ["RECIPIENT"]
    ntfy_topic = os.environ.get("NTFY_TOPIC", "")
    now = datetime.now(timezone.utc)

    sent = 0
    scan_args = {"FilterExpression": Attr("status").eq("active")}
    while True:
        page = table.scan(**scan_args)
        for item in page["Items"]:
            result = reminders_due(item, now)
            if result is None:
                continue
            label, to_mark = result

            if label is not None:
                subject, body = build_message(item, now)
                ses.send_email(
                    FromEmailAddress=sender,
                    Destination={"ToAddresses": [recipient]},
                    Content={
                        "Simple": {
                            "Subject": {"Data": subject},
                            "Body": {"Text": {"Data": body}},
                        }
                    },
                )
                send_push(ntfy_topic, subject, body, urgent=(label == "12h"))
                sent += 1
                print(f"Sent {label} reminder for {item['assignment_id']}")

            table.update_item(
                Key={"assignment_id": item["assignment_id"]},
                UpdateExpression="SET reminders_sent = list_append(reminders_sent, :new)",
                ExpressionAttributeValues={":new": to_mark},
            )

        if "LastEvaluatedKey" not in page:
            break
        scan_args["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    print(f"Done. Emails sent: {sent}")
    return {"emails_sent": sent}