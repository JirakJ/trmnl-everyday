from datetime import timedelta
from .calendars import load
from .common import number, screen, text


def render(events, config, now, *, demo=False):
    switch = int(number(config.get("tomorrow_after_hour", 18), "tomorrow_after_hour", 0, 23))
    day = now.date() + timedelta(days=int(now.hour >= switch))
    selected = [event for event in events if event["start"].date() <= day and event["end"].date() >= day
                and event["end"] > now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=(day - now.date()).days)
                and (day != now.date() or event["end"] > now)]
    rules = config.get("assignments", [])
    rows = []
    for event in selected[:5]:
        notes = []
        for line in event.get("description", "").splitlines():
            if line.lower().startswith(("pickup:", "bring:")):
                notes.append(text(line, 55))
        for rule in rules:
            if rule.get("event", "").casefold() == event["title"].casefold():
                if rule.get("pickup"):
                    notes.append("Pickup: " + text(rule["pickup"], 20))
                if rule.get("bring"):
                    notes.append("Bring: " + text(rule["bring"], 40))
        rows.append({"time": "All day" if event["all_day"] else event["start"].strftime("%H:%M"),
                     "title": text(f"{event['owner']} · {event['title']}", 60), "detail": text(" · ".join(notes), 85)})
    label = "Tomorrow" if day > now.date() else "Today"
    return screen("Family Day", label, day.strftime("%A %d %b"),
                  f"{len(selected)} upcoming events · first {min(5, len(selected))} shown", rows, now,
                  source="Private calendar titles hidden" if config.get("hide_private", True) else "Shared family calendars", demo=demo)


def collect(config, now):
    return render(load(config, now), config, now)


def demo(now):
    day = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=int(now.hour >= 18))
    events = [{"start": day + timedelta(hours=hour), "end": day + timedelta(hours=hour + 1), "all_day": False,
               "title": name, "owner": owner, "description": notes} for hour, name, owner, notes in
              [(14, "School pickup", "Alex", "Pickup: Sam\nBring: Sports bag"), (16, "Swimming", "Sam", "Bring: Towel"),
               (18, "Dinner together", "Everyone", ""), (20, "Prepare for tomorrow", "Everyone", "Bring: Library books")]]
    return render(events, {}, now, demo=True)
