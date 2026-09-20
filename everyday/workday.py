"""Compute available working time from the union of busy calendar intervals."""
from datetime import datetime, time, timedelta
from .calendars import load
from .common import number, screen, text


def plan(events, config, now):
    begin = time.fromisoformat(config.get("work_start", "09:00"))
    finish = time.fromisoformat(config.get("work_end", "17:00"))
    if begin.tzinfo or finish.tzinfo or finish <= begin:
        raise ValueError("Work hours must be local times within one day")
    weekdays = config.get("work_days", [0, 1, 2, 3, 4])
    if not weekdays or any(type(day) is not int or not 0 <= day <= 6 for day in weekdays):
        raise ValueError("work_days must contain weekday numbers 0–6")
    minimum = number(config.get("minimum_free_minutes", 30), "minimum_free_minutes", 5, 480) * 60
    day = now.date()
    for _ in range(8):
        start = datetime.combine(day, begin, now.tzinfo)
        end = datetime.combine(day, finish, now.tzinfo)
        if day.weekday() in weekdays and now < end:
            break
        day += timedelta(days=1)
    meetings = [event for event in events if event["busy"] and event["end"] > max(now, start) and event["start"] < end]
    cursor = max(start.timestamp(), now.timestamp())
    busy = sorted((max(cursor, event["start"].timestamp()), min(end.timestamp(), event["end"].timestamp())) for event in meetings)
    gaps = []
    for left, right in busy + [(end.timestamp(), end.timestamp())]:
        if left - cursor >= minimum:
            gaps.append((datetime.fromtimestamp(cursor, now.tzinfo), datetime.fromtimestamp(left, now.tzinfo)))
        cursor = max(cursor, right)
    return day, meetings, gaps


def render(events, config, now, *, demo=False):
    day, meetings, gaps = plan(events, config, now)
    duration = lambda gap: int((gap[1].timestamp() - gap[0].timestamp()) / 60)
    best = max(gaps, key=duration, default=None)
    rows = []
    if meetings:
        upcoming = min(meetings, key=lambda event: event["start"])
        name = "Busy" if config.get("hide_titles", False) else upcoming["title"]
        rows.append({"time": "Ongoing" if upcoming["start"] <= now else upcoming["start"].strftime("%H:%M"),
                     "title": text(name, 60), "detail": f"Next meeting · until {upcoming['end']:%H:%M}"})
    for left, right in gaps[:3]:
        rows.append({"time": left.strftime("%H:%M"), "title": f"{duration((left, right))} minutes free", "detail": f"Until {right:%H:%M}"})
    hero = f"{duration(best)} min" if best else "No block"
    detail = f"{day:%a %d %b} · {best[0]:%H:%M}–{best[1]:%H:%M}" if best else f"{day:%a %d %b} · no gap meets your minimum"
    metrics = [{"value": str(len(meetings)), "label": "Meetings left"},
               {"value": f"{sum(duration(gap) for gap in gaps)}m", "label": "Focus time"},
               {"value": max((event["end"] for event in meetings)).strftime("%H:%M") if meetings else "—", "label": "Last meeting ends"}]
    return screen("Workday Windows", hero, "Longest available block", detail, rows, now, metrics=metrics,
                  source="Based on calendar availability · titles hidden" if config.get("hide_titles") else "Based on calendar availability", demo=demo)


def collect(config, now):
    return render(load(config, now, days=8), config, now)


def demo(now):
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    demo_now = now.replace(hour=9, minute=0, second=0, microsecond=0)
    events = [{"start": start + timedelta(hours=left), "end": start + timedelta(hours=right), "busy": True, "title": title}
              for left, right, title in [(9.5, 10, "Planning"), (12, 13, "Team review"), (12.5, 13.5, "Customer call"), (15, 15.5, "Project update")]]
    return render(events, {"work_days": list(range(7))}, demo_now, demo=True)
