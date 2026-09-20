import unittest
from datetime import datetime, timezone
from everyday.outside import windows, demo
from everyday.common import packet


class OutsideTests(unittest.TestCase):
    def test_whole_window_and_missing_forecast(self):
        now = datetime(2026, 9, 20, 8, tzinfo=timezone.utc)
        hourly = {"time": [int(now.timestamp()) + 3600 * i for i in range(4)],
                  "temperature_2m": [20] * 4, "precipitation_probability": [0, 90, 0, 0],
                  "wind_speed_10m": [5] * 4, "is_day": [1] * 4}
        results = windows(hourly, {"duration_minutes": 120}, now)
        self.assertEqual([r["start"].hour for r in results], [10])
        hourly["temperature_2m"][2] = None
        self.assertEqual(windows(hourly, {"duration_minutes": 120}, now), [])
        hourly["temperature_2m"][2] = float("nan")
        self.assertEqual(windows(hourly, {"duration_minutes": 120}, now), [])
        hourly["temperature_2m"][2] = 20
        hourly["precipitation_probability"][2] = -1
        self.assertEqual(windows(hourly, {"duration_minutes": 120}, now), [])
        self.assertLess(len(packet(demo(now))), 2000)


if __name__ == "__main__":
    unittest.main()
