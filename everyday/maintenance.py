"""Recurring household jobs and local, single-use confirmation links."""
import calendar
import hashlib
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from urllib.parse import urlsplit
import qrcode
from .common import local_path, number, screen, text


def tasks(config):
    items = config.get("tasks", [])
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError("Configure 1–100 maintenance tasks")
    seen = set()
    for task in items:
        key = task["id"]
        if not re.fullmatch(r"[a-z0-9_-]{1,40}", key) or key in seen or not task.get("name"):
            raise ValueError("Tasks need unique simple IDs and names")
        seen.add(key)
        date.fromisoformat(task["last_done"])
        intervals = [field for field in ("interval_days", "interval_months") if field in task]
        if len(intervals) != 1:
            raise ValueError("Use exactly one interval: days or months")
        value = task[intervals[0]]
        limit = 36500 if intervals[0] == "interval_days" else 1200
        if int(number(value, intervals[0], 1, limit)) != value:
            raise ValueError("Maintenance intervals must be integers")
    return items


@contextmanager
def database(config):
    path = local_path(config, config.get("state_file", "maintenance.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Create with private permissions before SQLite opens it.
    import os
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    path.chmod(0o600)
    db = sqlite3.connect(path, timeout=10)
    try:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS completed (task_id TEXT PRIMARY KEY, day TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS actions (digest TEXT PRIMARY KEY, task_id TEXT NOT NULL,
                baseline TEXT NOT NULL, expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def last_done(db, task):
    row = db.execute("SELECT day FROM completed WHERE task_id = ?", (task["id"],)).fetchone()
    return date.fromisoformat(row[0] if row else task["last_done"])


def due_date(task, completed):
    if "interval_days" in task:
        return completed + timedelta(days=task["interval_days"])
    month = completed.year * 12 + completed.month - 1 + task["interval_months"]
    year, month = divmod(month, 12)
    month += 1
    return date(year, month, min(completed.day, calendar.monthrange(year, month)[1]))


def baseline(db, task):
    return hashlib.sha256((json.dumps(task, sort_keys=True) + last_done(db, task).isoformat()).encode()).hexdigest()


def base_url(config):
    value = config["confirmation_base_url"].rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("Confirmation URL must be an HTTP(S) origin without a path")
    if parsed.scheme != "https" and not config.get("allow_http", False):
        raise ValueError("Use HTTPS, or explicitly allow HTTP on a trusted local network")
    if len(value) > 100:
        raise ValueError("Use a shorter confirmation hostname to keep the QR code readable")
    return value


def issue_link(db, config, task, now):
    token = secrets.token_urlsafe(24)
    digest = hashlib.sha256(token.encode()).hexdigest()
    db.execute("DELETE FROM actions WHERE expires < ?", (int(now.timestamp()),))
    db.execute("INSERT INTO actions VALUES (?, ?, ?, ?)",
               (digest, task["id"], baseline(db, task), int(now.timestamp()) + 7 * 86400))
    return f"{base_url(config)}/complete/{token}"


def action_task(db, config, token, now):
    if not re.fullmatch(r"[A-Za-z0-9_-]{32}", token):
        raise ValueError("Invalid or expired link")
    row = db.execute("SELECT task_id, baseline, expires FROM actions WHERE digest = ?",
                     (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    task = next((item for item in tasks(config) if row and item["id"] == row[0]), None)
    if not task or row[2] <= now.timestamp() or not secrets.compare_digest(row[1], baseline(db, task)):
        raise ValueError("Invalid or expired link")
    return task


def complete(config, token, now):
    with database(config) as db:
        db.execute("BEGIN IMMEDIATE")
        task = action_task(db, config, token, now)
        db.execute("INSERT INTO completed VALUES (?, ?) ON CONFLICT(task_id) DO UPDATE SET day=excluded.day",
                   (task["id"], now.date().isoformat()))
        db.execute("DELETE FROM actions WHERE task_id = ?", (task["id"],))
    return task


def qr_data(url):
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    code.add_data(url)
    code.make(fit=True)
    matrix = code.get_matrix()
    size = len(matrix)
    width = (size + 3) // 4
    encoded = "".join(f"{int(''.join('1' if cell else '0' for cell in row), 2):0{width}x}" for row in matrix)
    return {"qr_size": size, "qr_bits": encoded}


def render(items, now, url, *, demo=False):
    items.sort(key=lambda item: item[1])
    today = now.date()
    rows = []
    for task, due in items[:4]:
        days = (due - today).days
        status = f"{abs(days)}d late" if days < 0 else ("Today" if days == 0 else f"In {days}d")
        rows.append({"time": status, "title": text(task["name"], 40), "detail": f"Due {due:%d %b %Y}"})
    overdue = sum(due < today for task, due in items)
    result = screen("Home Maintenance", f"{overdue} overdue" if overdue else rows[0]["time"], "Keep your home running",
                    "Scan to confirm the first task", rows, now, source="Next interval starts on the completion date", demo=demo)
    result.update(qr_data(url))
    return result


def collect(config, now):
    with database(config) as db:
        items = [(task, due_date(task, last_done(db, task))) for task in tasks(config)]
        items.sort(key=lambda item: item[1])
        url = issue_link(db, config, items[0][0], now)
    return render(items, now, url)


def demo(now):
    items = [({"name": name}, now.date() + timedelta(days=days))
             for name, days in (("Replace ventilation filter", -3), ("Descale coffee machine", 0),
                                ("Check smoke alarms", 6), ("Clean dishwasher filter", 12))]
    return render(items, now, "https://example.invalid/maintenance-demo", demo=True)
