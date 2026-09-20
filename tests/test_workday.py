import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from everyday.workday import plan, render


class WorkdayTests(unittest.TestCase):
    def test_interval_union_and_private_titles(self):
        now = datetime(2026, 9, 21, 9, tzinfo=ZoneInfo("Europe/Prague"))
        def event(a, b, busy=True):
            return {"start": now + timedelta(hours=a), "end": now + timedelta(hours=b), "busy": busy, "title": "Secret project"}
        events = [event(0, 3), event(1, 2), event(2.5, 4), event(5, 6, False)]
        day, meetings, gaps = plan(events, {}, now)
        self.assertEqual([(a.hour, b.hour) for a, b in gaps], [(13, 17)])
        data = render(events, {"hide_titles": True}, now)
        self.assertNotIn("Secret project", str(data))
        self.assertEqual(plan([event(-9, 15)], {}, now)[2], [])
        sunday = now - timedelta(days=1)
        self.assertEqual(plan([], {}, sunday)[0], now.date())


if __name__ == "__main__":
    unittest.main()
