"""Local dusk clock for a stored show.

The Pi uses its own time. Sunset is calculated from a latitude and longitude,
so the PC does not have to stay on.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone


def clean(value: object) -> dict:
    raw = value if isinstance(value, dict) else {}
    latitude = _coord(raw.get("latitude"), -90, 90)
    longitude = _coord(raw.get("longitude"), -180, 180)
    after = raw.get("afterSunset", 20)
    if isinstance(after, bool) or not isinstance(after, (int, float)):
        after = 20
    after = int(after)
    if after < -60 or after > 180:
        after = 20
    end = _clock_time(raw.get("end"), "23:00")
    return {
        "enabled": raw.get("enabled") is True,
        "latitude": latitude,
        "longitude": longitude,
        "afterSunset": after,
        "start": _clock_time(raw.get("start"), ""),
        "end": end,
    }


def sunset(day: date, latitude: float, longitude: float) -> datetime | None:
    """Official sunset in UTC. None during polar day or night."""
    julian = _julian_sunset(day, latitude, longitude)
    if julian is None:
        return None
    return datetime.fromtimestamp((julian - 2440587.5) * 86400, timezone.utc)


def _julian_sunset(day: date, latitude: float, longitude: float) -> float | None:
    """Julian date of sunset, from the sunrise equation."""
    days = (datetime(day.year, day.month, day.day) - datetime(2000, 1, 1)).days + 0.0008
    solar_noon = days - longitude / 360
    anomaly = math.radians((357.5291 + 0.98560028 * solar_noon) % 360)
    center = math.radians(1.9148 * math.sin(anomaly) + 0.0200 * math.sin(2 * anomaly) + 0.0003 * math.sin(3 * anomaly))
    ecliptic = math.radians((math.degrees(anomaly) + math.degrees(center) + 180 + 102.9372) % 360)
    transit = 2451545.0 + solar_noon + 0.0053 * math.sin(anomaly) - 0.0069 * math.sin(2 * ecliptic)
    declination = math.sin(ecliptic) * math.sin(math.radians(23.4397))
    cosine = math.cos(math.radians(latitude)) * math.cos(math.asin(declination))
    if abs(cosine) < 1e-6:
        return None
    argument = (math.sin(math.radians(-0.833)) - math.sin(math.radians(latitude)) * declination) / cosine
    if argument > 1 or argument < -1:
        return None
    return transit + math.degrees(math.acos(argument)) / 360


def status(saved: object, now: datetime) -> dict:
    """Describe tonight's window. active is None when the clock is off."""
    saved = clean(saved)
    local = now.astimezone(now.tzinfo) if now.tzinfo else datetime.now().astimezone()
    result = {
        **saved,
        "now": _clock(local),
        "starts": "",
        "stops": _clock(_on_day(local, saved["end"])),
        "on": False,
        "active": None,
        "note": "",
    }
    if not saved["enabled"]:
        return result
    if not saved["start"] and (saved["latitude"] is None or saved["longitude"] is None):
        result["active"] = False
        result["note"] = "Enter the latitude and longitude for this house."
        return result
    windows = []
    for day in (local.date() - timedelta(days=1), local.date()):
        window = _window(day, saved, local.tzinfo)
        if window:
            windows.append(window)
    if not windows:
        result["active"] = False
        result["note"] = "This location has no sunset on that date."
        return result
    tonight = windows[-1]
    result["starts"] = _clock(tonight[0].astimezone(local.tzinfo))
    result["stops"] = _clock(tonight[1].astimezone(local.tzinfo))
    result["on"] = any(start <= local < stop for start, stop in windows)
    result["active"] = result["on"]
    if result["on"]:
        result["note"] = f"The stored show is on until {result['stops']}."
    else:
        result["note"] = f"The stored show starts at {result['starts']} and stops at {result['stops']}."
    return result


def _window(day: date, saved: dict, zone) -> tuple[datetime, datetime] | None:
    if saved["start"]:
        hour, minute = (int(part) for part in saved["start"].split(":"))
        start = datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone)
    else:
        event = sunset(day, saved["latitude"], saved["longitude"])
        if event is None:
            return None
        start = event.astimezone(zone) + timedelta(minutes=saved["afterSunset"])
    stop = _on_day(start, saved["end"])
    if stop <= start:
        stop += timedelta(days=1)
    return start, stop


def _on_day(moment: datetime, end: str) -> datetime:
    hour, minute = (int(part) for part in end.split(":"))
    return moment.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _clock_time(value: object, default: str) -> str:
    if value is None or value == "":
        return "" if default == "" else default
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        return default
    hour, minute = value.split(":", 1)
    if not (hour.isdigit() and minute.isdigit() and int(hour) < 24 and int(minute) < 60):
        return default
    return f"{int(hour):02d}:{int(minute):02d}"


def _coord(value: object, low: float, high: float) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < low or number > high:
        return None
    return round(number, 5)


def _clock(moment: datetime) -> str:
    hour = moment.hour % 12 or 12
    return f"{hour}:{moment.minute:02d} {'AM' if moment.hour < 12 else 'PM'}"
