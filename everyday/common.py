"""Shared I/O. No credentials or source payloads are logged."""
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PLUGINS = ("outside", "family", "workday")
UTC = timezone.utc


def number(value, name, low, high):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


def text(value, limit=70):
    return " ".join(str(value).split())[:limit]


def instant(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp needs a UTC offset")
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward private calendar URLs or authorization across redirects.
        raise ValueError("Redirect refused; configure the final HTTPS URL")


def request(url, *, payload=None, headers=None, allow_http=False):
    parsed = urllib.parse.urlsplit(url)
    schemes = ("https", "http") if allow_http else ("https",)
    if parsed.scheme not in schemes or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Use a valid HTTPS URL without embedded credentials")
    req = urllib.request.Request(url, data=payload, headers={"User-Agent": "trmnl-everyday/0.1", **(headers or {})})
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=20) as response:
            data = response.read(5_000_001)
    except urllib.error.HTTPError as error:
        raise ValueError(f"Remote service returned HTTP {error.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ValueError("Remote service unavailable; previous display data was preserved") from None
    if len(data) > 5_000_000:
        raise ValueError("Source response exceeds 5 MB")
    return data


def get_json(url, **kwargs):
    return json.loads(request(url, **kwargs))


def read_config(path):
    path = Path(path).resolve()
    config = json.loads(path.read_text())
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object")
    config["_base"] = str(path.parent)
    return config


def local_path(config, value):
    return Path(config.get("_base", ".")) / value


def clock(config, now=None):
    return (now or datetime.now(UTC)).astimezone(ZoneInfo(config.get("timezone", "Europe/Prague")))


def screen(title, hero, label, detail, rows, now, *, metrics=(), source="", demo=False):
    return {"title": text(title, 32), "hero": text(hero, 24), "hero_label": text(label, 40),
            "detail": text(detail, 120), "rows": rows[:6], "metrics": list(metrics)[:3],
            "updated": now.strftime("%d %b %H:%M %Z"), "source": text(source, 90), "demo": demo}


def packet(data):
    payload = json.dumps({"merge_variables": data}, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    if len(payload) > 2000:
        raise ValueError(f"Payload is {len(payload)} bytes; reduce labels/items to fit the 2000-byte budget")
    return payload


def push(data):
    if data.get("demo"):
        raise ValueError("Demo data cannot be pushed; use your own configuration")
    url = os.environ.get("TRMNL_WEBHOOK_URL", "")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "trmnl.com" or not re.fullmatch(r"/api/custom_plugins/[A-Za-z0-9_-]+", parsed.path) or parsed.query or parsed.fragment:
        raise ValueError("Set TRMNL_WEBHOOK_URL to your trmnl.com private plugin webhook URL")
    response = request(url, payload=packet(data), headers={"Content-Type": "application/json"})
    if response:
        result = json.loads(response)
        if isinstance(result, dict) and (result.get("error") or result.get("status", 200) not in (200, 201, "success", "ok")):
            raise ValueError("TRMNL did not accept the update")
