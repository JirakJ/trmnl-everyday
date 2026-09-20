import unittest
from datetime import datetime, timedelta, timezone
from everyday.homelab import backup_status, collect


class HomelabTests(unittest.TestCase):
    def test_stale_missing_and_failed_checks(self):
        now = datetime(2026, 9, 20, tzinfo=timezone.utc)
        data = [{"time": (now - timedelta(hours=30)).isoformat(), "hostname": "nas"}]
        self.assertEqual(backup_status(data, {}, now)[0], "STALE")
        self.assertEqual(backup_status(data, {"host": "other"}, now)[0], "MISSING")
        self.assertEqual(backup_status([{"time": (now + timedelta(hours=1)).isoformat()}], {}, now)[0], "UNKNOWN")
        screen = collect({"checks": [{"name": "Backup", "kind": "restic_file", "file": "/nonexistent/snapshots.json"}]}, now)
        self.assertEqual(screen["hero"], "1 issue")
        self.assertEqual(screen["rows"][0]["time"], "UNKNOWN")
        self.assertNotIn("/nonexistent", str(screen))


if __name__ == "__main__":
    unittest.main()
