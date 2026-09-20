"""Repeating shift rotas, date exceptions and genuinely shared days off."""
from datetime import date, datetime, time, timedelta
from .common import screen, text


def shift(person, day, tz):
    cycle = person.get("cycle", [])
    definitions = person.get("shifts", {})
    if not cycle or len(cycle) > 366 or any(code not in definitions for code in cycle):
        raise ValueError("Define a 1–366 day cycle using known shift codes")
    offset = (day - date.fromisoformat(person["anchor"])).days
    code = person.get("exceptions", {}).get(day.isoformat(), cycle[offset % len(cycle)])
    if code not in definitions:
        raise ValueError("Exception references an unknown shift code")
    definition = definitions[code]
    if definition is None:
        return None
    start_time, end_time = time.fromisoformat(definition["start"]), time.fromisoformat(definition["end"])
    if start_time.tzinfo or end_time.tzinfo or start_time == end_time:
        raise ValueError("Shift hours must be distinct local times")
    start = datetime.combine(day, start_time, tz)
    end = datetime.combine(day + timedelta(days=int(end_time < start_time)), end_time, tz)
    return {"code": text(code, 12), "start": start, "end": end}


def day_off(person, day, tz):
    midnight = datetime.combine(day, time.min, tz)
    tomorrow = midnight + timedelta(days=1)
    for origin in (day - timedelta(days=1), day):
        duty = shift(person, origin, tz)
        if duty and duty["end"] > midnight and duty["start"] < tomorrow:
            return False
    return True


def collect(config, now, *, demo=False):
    people = config.get("people", [])
    if not isinstance(people, list) or not 1 <= len(people) <= 4:
        raise ValueError("Configure 1–4 people")
    next_duties = []
    for person in people:
        for i in range(-1, 57):
            duty = shift(person, now.date() + timedelta(days=i), now.tzinfo)
            if duty and duty["end"] > now:
                next_duties.append({**duty, "name": text(person["name"], 20)})
                break
    next_duties.sort(key=lambda duty: duty["start"])
    free_days = [now.date() + timedelta(days=i) for i in range(56)
                 if all(day_off(person, now.date() + timedelta(days=i), now.tzinfo) for person in people)]
    weekend = next((day for day in free_days if day.weekday() == 5 and day + timedelta(days=1) in free_days), None)
    rows = []
    for i in range(4):
        day = now.date() + timedelta(days=i)
        titles, hours = [], []
        for person in people:
            duty = shift(person, day, now.tzinfo)
            name = text(person["name"], 16)
            titles.append(f"{name}: {duty['code'] if duty else 'Off'}")
            if duty:
                hours.append(f"{name} {duty['start']:%H:%M}–{duty['end']:%H:%M}")
            elif not day_off(person, day, now.tzinfo):
                hours.append(f"{name}: night shift ends today")
        rows.append({"time": day.strftime("%a %d"), "title": text(" · ".join(titles), 65), "detail": text(" · ".join(hours) or "Full day off", 85)})
    duty = next_duties[0] if next_duties else None
    hero = duty["code"] if duty else "Off"
    label = f"{duty['name']} · {'on duty' if duty['start'] <= now else 'next shift'}" if duty else "No shifts in 8 weeks"
    detail = f"{duty['start']:%a %d %b %H:%M} → {duty['end']:%a %H:%M}" if duty else "Check your schedule"
    metrics = [{"label": "Shared day off", "value": free_days[0].strftime("%d %b") if free_days else "None"},
               {"label": "Shared weekend", "value": weekend.strftime("%d %b") if weekend else "None"}]
    return screen("Shift Together", hero, label, detail, rows, now, metrics=metrics, source="Local rota · search horizon 8 weeks", demo=demo)


def demo(now):
    definitions = {"Day": {"start": "07:00", "end": "19:00"}, "Night": {"start": "19:00", "end": "07:00"}, "Off": None}
    people = [{"name": name, "anchor": (now.date() - timedelta(days=offset)).isoformat(), "cycle": ["Day", "Day", "Night", "Night", "Off", "Off", "Off", "Off"], "shifts": definitions}
              for name, offset in [("Alex", 2), ("Sam", 3)]]
    return collect({"people": people}, now, demo=True)
