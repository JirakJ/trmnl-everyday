import re
import tempfile
import unittest
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from everyday.maintenance import action_task, collect, database, due_date, issue_link, last_done
from everyday.maintenance_server import create_app
from everyday.common import packet


class MaintenanceTests(unittest.TestCase):
    def test_dates_confirmation_privacy_and_replay(self):
        now = datetime(2026, 9, 20, 12, tzinfo=ZoneInfo("Europe/Prague"))
        task = {"id": "filter", "name": "Filter <script>alert(1)</script>", "last_done": "2026-08-01", "interval_months": 1}
        self.assertEqual(due_date(task, date(2026, 1, 31)), date(2026, 2, 28))
        with tempfile.TemporaryDirectory() as directory:
            config = {"_base": directory, "tasks": [task], "confirmation_base_url": "http://localhost:8765", "allow_http": True}
            with database(config) as db:
                url = issue_link(db, config, task, now)
                second = issue_link(db, config, task, now).split("/")[-1]
            path = "/complete/" + url.split("/")[-1]
            app = create_app(config, lambda: now)
            client = app.test_client()
            self.assertEqual(client.post(path).status_code, 403)
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(b"<script>", response.data)
            self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
            csrf = re.search(r'name="csrf" value="([^"]+)"', response.text)[1]
            with database(config) as db:
                self.assertEqual(last_done(db, task), date(2026, 8, 1))
                with self.assertRaises(ValueError):
                    action_task(db, config, second, now + timedelta(days=8))
            self.assertEqual(client.post(path, data={"csrf": csrf}, headers={"Origin": "https://evil.invalid"}).status_code, 403)
            self.assertEqual(client.get(path, headers={"Host": "evil.invalid"}).status_code, 400)
            self.assertEqual(client.post(path, data={"csrf": csrf}, headers={"Origin": "http://localhost:8765"}).status_code, 303)
            self.assertIn(b"Saved", client.get("/saved").data)
            self.assertEqual(client.get(path).status_code, 410)
            with database(config) as db:
                self.assertEqual(last_done(db, task), now.date())
                with self.assertRaises(ValueError):
                    action_task(db, config, second, now)
            self.assertEqual(Path(directory, "maintenance.sqlite3").stat().st_mode & 0o777, 0o600)
            self.assertLessEqual(len(packet(collect(config, now))), 2000)

    def test_changed_task_invalidates_previous_link(self):
        now = datetime(2026, 9, 20, tzinfo=ZoneInfo("Europe/Prague"))
        with tempfile.TemporaryDirectory() as directory:
            task = {"id": "filter", "name": "Filter", "last_done": "2026-08-01", "interval_days": 30}
            config = {"_base": directory, "tasks": [task], "confirmation_base_url": "https://home.example"}
            with database(config) as db:
                token = issue_link(db, config, task, now).split("/")[-1]
                task["interval_days"] = 60
                with self.assertRaises(ValueError):
                    action_task(db, config, token, now)


if __name__ == "__main__":
    unittest.main()
