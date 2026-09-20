import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo
from everyday.shifts import shift, day_off, collect
from everyday.common import packet


class ShiftTests(unittest.TestCase):
    def test_overnight_exception_and_dst(self):
        tz = ZoneInfo("Europe/Prague")
        person = {"name": "Alex", "anchor": "2026-10-24", "cycle": ["Night", "Off", "Off"],
                  "shifts": {"Night": {"start": "19:00", "end": "07:00"}, "Off": None}, "exceptions": {}}
        duty = shift(person, date(2026, 10, 24), tz)
        self.assertEqual((duty["end"].timestamp() - duty["start"].timestamp()) / 3600, 13)
        self.assertFalse(day_off(person, date(2026, 10, 25), tz))
        self.assertTrue(day_off(person, date(2026, 10, 23), tz))
        self.assertEqual(collect({"people": [person]}, datetime(2026, 10, 25, 3, tzinfo=tz))["hero"], "Night")
        person["exceptions"]["2026-10-24"] = "Off"
        self.assertTrue(day_off(person, date(2026, 10, 25), tz))
        packet(collect({"people": [person]}, datetime(2026, 10, 25, 3, tzinfo=tz)))


if __name__ == "__main__":
    unittest.main()
