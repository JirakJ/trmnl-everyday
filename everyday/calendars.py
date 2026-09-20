"""Read ICS feeds using a recurrence-aware parser, shared by family and workday."""
import os
from datetime import date, datetime, time, timedelta
import icalendar
import recurring_ical_events
from .common import ConfigurationError, local_path, request, text


def parse(raw, owner, start, end, *, hide_private=True):
    if len(raw) > 5_000_000 or b"BEGIN:VCALENDAR" not in raw:
        raise ConfigurationError("Expected an ICS calendar under 5 MB")
    calendar = icalendar.Calendar.from_ical(raw)
    result = []
    for event in recurring_ical_events.of(calendar).between(start, end):
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        begin = event.decoded("DTSTART")
        finish = event.decoded("DTEND", None)
        all_day = isinstance(begin, date) and not isinstance(begin, datetime)
        if finish is None:
            finish = begin + event.decoded("DURATION", timedelta(days=1) if all_day else timedelta())
        def aware(value):
            if not isinstance(value, datetime):
                return datetime.combine(value, time.min, tzinfo=start.tzinfo)
            return value.replace(tzinfo=start.tzinfo) if value.tzinfo is None else value.astimezone(start.tzinfo)
        begin, finish = aware(begin), aware(finish)
        if finish < begin:
            raise ConfigurationError("Calendar event ends before it starts")
        if finish <= start or begin >= end:
            continue
        private = str(event.get("CLASS", "")).upper() in ("PRIVATE", "CONFIDENTIAL")
        title = "Private event" if private and hide_private else text(event.get("SUMMARY", "Untitled event"), 60)
        description = "" if private and hide_private else str(event.get("DESCRIPTION", ""))
        result.append({"start": begin, "end": finish, "all_day": all_day, "title": title,
                       "owner": text(owner, 20), "description": description,
                       "busy": str(event.get("TRANSP", "OPAQUE")).upper() != "TRANSPARENT"})
    return sorted(result, key=lambda event: event["start"])


def load(config, now, days=2):
    sources = config.get("calendars", [])
    if not isinstance(sources, list) or not 1 <= len(sources) <= 12:
        raise ConfigurationError("Configure 1–12 calendars")
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = []
    for source in sources:
        if "url_env" in source:
            raw = request(os.environ[source["url_env"]])
        elif "file" in source:
            path = local_path(config, source["file"])
            if path.stat().st_size > 5_000_000:
                raise ConfigurationError("Calendar exceeds 5 MB")
            raw = path.read_bytes()
        else:
            raise ConfigurationError("Each calendar needs file or url_env")
        result.extend(parse(raw, source.get("name", "Calendar"), start, start + timedelta(days=days), hide_private=config.get("hide_private", True)))
    return sorted(result, key=lambda event: event["start"])
