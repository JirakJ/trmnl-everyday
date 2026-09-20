"""Rank contiguous daylight windows, including every hour of the activity."""
from datetime import datetime, timedelta
import math
from urllib.parse import urlencode
from .common import ConfigurationError, UTC, get_json, number, screen, text

PRESETS = {"walk": (0, 30, 25, 30), "run": (0, 25, 20, 25), "cycle": (5, 30, 20, 20)}


def windows(hourly, config, now):
    activity = config.get("activity", "walk")
    if activity not in PRESETS:
        raise ConfigurationError("Activity must be walk, run or cycle")
    low, high, wind, rain = PRESETS[activity]
    low = number(config.get("min_temperature", low), "min_temperature", -40, 50)
    high = number(config.get("max_temperature", high), "max_temperature", low, 60)
    wind = number(config.get("max_wind_kmh", wind), "max_wind_kmh", 0, 150)
    rain = number(config.get("max_rain_probability", rain), "max_rain_probability", 0, 100)
    duration = int(number(config.get("duration_minutes", 60), "duration_minutes", 30, 240))
    fields = ("temperature_2m", "precipitation_probability", "wind_speed_10m", "is_day")
    times = hourly["time"]
    if any(len(hourly[key]) != len(times) for key in fields):
        raise ConfigurationError("Incomplete hourly forecast")
    candidates = []
    needed = (duration + 59) // 60
    for i in range(len(times) - needed + 1):
        start = datetime.fromtimestamp(times[i], UTC)
        if start < now or start > now + timedelta(days=3):
            continue
        values = [hourly[key][i:i + needed] for key in fields]
        temps, rains, winds, daylight = values
        if any(value is None for series in values for value in series):
            continue
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
               for series in (temps, rains, winds) for value in series):
            continue
        if any(not 0 <= value <= 100 for value in rains) or any(value < 0 for value in winds):
            continue
        if any(times[i + j] - times[i] != 3600 * j for j in range(needed)):
            continue
        if not all(v == 1 for v in daylight) or min(temps) < low or max(temps) > high or max(winds) > wind or max(rains) > rain:
            continue
        end = start + timedelta(minutes=duration)
        score = max(rains) * 2 + max(winds) + abs(sum(temps) / len(temps) - (low + high) / 2)
        candidates.append({"start": start, "end": end, "score": score, "temperature": round(sum(temps) / len(temps)), "rain": max(rains), "wind": round(max(winds))})
    selected = []
    for item in sorted(candidates, key=lambda v: (v["score"], v["start"])):
        if all(item["end"] <= other["start"] or item["start"] >= other["end"] for other in selected):
            selected.append(item)
        if len(selected) == 3:
            break
    return selected


def render(hourly, config, now, city, *, demo=False):
    found = windows(hourly, config, now)
    rows = []
    for item in found:
        start, end = (item[key].astimezone(now.tzinfo) for key in ("start", "end"))
        rows.append({"time": start.strftime("%a %H:%M"), "title": f"Until {end:%H:%M} · {item['temperature']}°C", "detail": f"Rain {item['rain']}% · wind {item['wind']} km/h"})
    best = found[0]["start"].astimezone(now.tzinfo).strftime("%a %H:%M") if found else "No window"
    return screen("Outside Window", best, f"Best time to {config.get('activity', 'walk')}",
                  f"{city} · {config.get('duration_minutes', 60)} minutes · next 72 hours", rows, now,
                  source="Open-Meteo / GeoNames · forecast, not a guarantee", demo=demo)


def collect(config, now):
    city = text(config.get("city", ""), 80)
    if not city:
        raise ConfigurationError("Set a city")
    if "latitude" in config and "longitude" in config:
        lat = number(config["latitude"], "latitude", -90, 90)
        lon = number(config["longitude"], "longitude", -180, 180)
    else:
        query = {"name": city, "count": 5, "language": "en"}
        if config.get("country_code"):
            query["countryCode"] = config["country_code"]
        locations = get_json("https://geocoding-api.open-meteo.com/v1/search?" + urlencode(query)).get("results", [])
        if len(locations) != 1:
            raise ConfigurationError("City is missing or ambiguous; set explicit latitude and longitude")
        lat, lon = locations[0]["latitude"], locations[0]["longitude"]
    query = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,is_day",
             "forecast_days": 4, "timeformat": "unixtime", "timezone": "UTC", "wind_speed_unit": "kmh"}
    endpoint = "https://api.open-meteo.com/v1/forecast"
    if config.get("weather_api_key_env"):
        import os
        query["apikey"] = os.environ[config["weather_api_key_env"]]
        endpoint = "https://customer-api.open-meteo.com/v1/forecast"
    forecast = get_json(endpoint + "?" + urlencode(query))
    return render(forecast["hourly"], config, now, city)


def demo(now):
    start = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    hourly = {"time": [int((start + timedelta(hours=i)).timestamp()) for i in range(72)],
              "temperature_2m": [18 + i % 5 for i in range(72)], "precipitation_probability": [10 if i % 8 < 5 else 80 for i in range(72)],
              "wind_speed_10m": [12] * 72, "is_day": [int(7 <= (start + timedelta(hours=i)).astimezone(now.tzinfo).hour < 19) for i in range(72)]}
    return render(hourly, {"activity": "walk", "duration_minutes": 60}, now, "Prague", demo=True)
