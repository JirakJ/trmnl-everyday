"""Read-only disk, HTTP service and restic snapshot checks."""
import json
import shutil
import subprocess
from datetime import timedelta
from .common import ConfigurationError, instant, local_path, number, request, screen, text


def backup_status(snapshots, check, now):
    if not isinstance(snapshots, list):
        raise ConfigurationError("Expected a restic snapshots array")
    if check.get("host"):
        snapshots = [item for item in snapshots if item.get("hostname") == check["host"]]
    if check.get("path"):
        snapshots = [item for item in snapshots if check["path"] in item.get("paths", [])]
    if not snapshots:
        return "MISSING", "No matching snapshot"
    latest = max(instant(item["time"]) for item in snapshots)
    age = (now.timestamp() - latest.timestamp()) / 3600
    limit = number(check.get("max_age_hours", 26), "max_age_hours", 1, 8760)
    if age < 0:
        return "UNKNOWN", "Snapshot timestamp is in the future"
    return ("STALE" if age > limit else "OK"), f"Last backup {age:.1f}h ago · limit {limit:g}h"


def run_check(check, config, now):
    kind = check["kind"]
    if kind == "disk":
        usage = shutil.disk_usage(local_path(config, check["path"]))
        used = (1 - usage.free / usage.total) * 100
        limit = number(check.get("warn_used_percent", 85), "warn_used_percent", 1, 99)
        return ("LOW" if used >= limit else "OK"), f"{usage.free / 2**30:.1f} GiB free · {used:.0f}% used"
    if kind == "http":
        request(check["url"], allow_http=check.get("allow_http", False), method="HEAD")
        return "OK", "Health endpoint responded successfully"
    if kind in ("restic", "restic_file"):
        if kind == "restic":
            command = ["restic", "snapshots", "--json", "--latest", "1"]
            for key in ("host", "path"):
                if check.get(key):
                    command.extend(["--" + key, check[key]])
            result = subprocess.run(command, capture_output=True, timeout=45, stdin=subprocess.DEVNULL)
            if result.returncode:
                return "ERROR", "Restic could not read the repository"
            raw = result.stdout
        else:
            path = local_path(config, check["file"])
            if path.stat().st_size > 5_000_000:
                raise ConfigurationError("Snapshot file exceeds 5 MB")
            raw = path.read_bytes()
        return backup_status(json.loads(raw), check, now)
    raise ConfigurationError("Unknown homelab check kind")


def render(results, now, *, demo=False):
    results = sorted(results, key=lambda row: row["time"] == "OK")
    problems = sum(row["time"] != "OK" for row in results)
    return screen("Homelab Watch", (f"{problems} issue" + ("s" if problems != 1 else "")) if problems else "All clear", "Read-only health checks",
                  f"{len(results)} checks · {min(5, len(results))} shown, problems first", results[:5], now,
                  source="Snapshot age does not verify restore integrity", demo=demo)


def collect(config, now):
    checks = config.get("checks", [])
    if not isinstance(checks, list) or not 1 <= len(checks) <= 8:
        raise ConfigurationError("Configure 1–8 named checks")
    results = []
    for check in checks:
        try:
            status, detail = run_check(check, config, now)
        except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError, subprocess.SubprocessError):
            status, detail = "UNKNOWN", "Check failed · inspect source/configuration"
        results.append({"time": status, "title": text(check.get("name", "Unnamed check"), 55), "detail": text(detail, 90)})
    return render(results, now)


def demo(now):
    status, detail = backup_status([{"time": (now - timedelta(hours=31)).isoformat()}], {}, now)
    return render([{"time": status, "title": "NAS backup", "detail": detail},
                   {"time": "LOW", "title": "Media volume", "detail": "42.0 GiB free · 92% used"},
                   {"time": "OK", "title": "Home Assistant", "detail": "Health endpoint responded successfully"},
                   {"time": "OK", "title": "System volume", "detail": "120.0 GiB free · 53% used"}], now, demo=True)
