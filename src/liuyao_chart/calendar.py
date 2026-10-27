"""Four pillars and xunkong for the cast moment, via lunar-python.

Liuyao convention: 23:00 (子初) already belongs to the next day pillar.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .tables import GAN, ZHI


def _xunkong(day_pillar: str) -> list[str]:
    gan = GAN.index(day_pillar[0])
    zhi = ZHI.index(day_pillar[1])
    xun_start = (zhi - gan) % 12
    return [ZHI[(xun_start - 2) % 12], ZHI[(xun_start - 1) % 12]]


def _four_pillars(cast_time: datetime, timezone: str | None = None) -> tuple[dict[str, str], list[str]]:
    if timezone is None:
        tz_name = getattr(cast_time.tzinfo, "key", None)
        if not tz_name:
            raise ValueError("an aware datetime or an explicit timezone is required")
    else:
        tz_name = timezone
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown IANA timezone: {tz_name}") from exc
    local = cast_time.astimezone(tz)
    # 23:00 changes the day pillar (子初换日).
    day_local = local + timedelta(days=1) if local.hour >= 23 else local
    from lunar_python import Solar

    civil_ec = Solar.fromYmdHms(
        local.year, local.month, local.day, local.hour, local.minute, local.second
    ).getLunar().getEightChar()
    day_ec = Solar.fromYmdHms(
        day_local.year, day_local.month, day_local.day,
        day_local.hour, day_local.minute, day_local.second
    ).getLunar().getEightChar()
    day_pillar = day_ec.getDay()
    hour_branch = ((local.hour + 1) // 2) % 12
    hour_stem = (GAN.index(day_pillar[0]) % 5 * 2 + hour_branch) % 10
    pillars = {
        "year": civil_ec.getYear(),
        "month": civil_ec.getMonth(),
        "day": day_pillar,
        "hour": GAN[hour_stem] + ZHI[hour_branch],
    }
    return pillars, _xunkong(day_pillar)
