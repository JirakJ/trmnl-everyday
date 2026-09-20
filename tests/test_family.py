import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from everyday.calendars import parse
from everyday.family import render

ICS = b'''BEGIN:VCALENDAR\r
VERSION:2.0\r
BEGIN:VEVENT\r
UID:daily-example\r
DTSTART;TZID=Europe/Prague:20260920T140000\r
DTEND;TZID=Europe/Prague:20260920T150000\r
RRULE:FREQ=DAILY;COUNT=3\r
EXDATE;TZID=Europe/Prague:20260921T140000\r
SUMMARY:Confidential meeting\r
CLASS:PRIVATE\r
DESCRIPTION:Bring: Secret notes\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:cancelled-example\r
DTSTART;TZID=Europe/Prague:20260920T160000\r
DTEND;TZID=Europe/Prague:20260920T170000\r
SUMMARY:Cancelled event\r
STATUS:CANCELLED\r
END:VEVENT\r
END:VCALENDAR\r
'''


class FamilyTests(unittest.TestCase):
    def test_ics_recurrence_privacy_and_evening(self):
        now = datetime(2026, 9, 20, 12, tzinfo=ZoneInfo("Europe/Prague"))
        events = parse(ICS, "Family", now.replace(hour=0), now.replace(day=23, hour=0))
        self.assertEqual([e["start"].day for e in events], [20, 22])
        self.assertEqual(events[0]["title"], "Private event")
        self.assertEqual(events[0]["description"], "")
        self.assertEqual(len(render(events, {}, now)["rows"]), 1)
        evening = render(events, {}, now.replace(hour=19))
        self.assertEqual(evening["hero"], "Tomorrow")
        self.assertEqual(evening["rows"], [])


if __name__ == "__main__":
    unittest.main()
