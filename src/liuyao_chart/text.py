"""Plain-text rendering of a computed chart (no LLM prompt framing)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from unicodedata import east_asian_width
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .tables import LIUHE_BITS, PALACE_TABLE


_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value or {})


def _local_cast_time(chart: Mapping[str, Any]) -> datetime:
    raw = chart.get("cast_time")
    if isinstance(raw, datetime):
        cast_time = raw
    elif isinstance(raw, str) and raw:
        cast_time = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    else:
        raise ValueError("cast_time is required to render the chart text.")
    if cast_time.tzinfo is None or cast_time.utcoffset() is None:
        raise ValueError("cast_time must include a UTC offset to render the chart text.")

    timezone = str(chart.get("timezone") or "")
    if timezone:
        try:
            return cast_time.astimezone(ZoneInfo(timezone))
        except ZoneInfoNotFoundError:
            pass
    # 不退回运行机器的本地时区：同一张盘在任何机器上都渲染出同样的文本。
    return cast_time


def _lunar_date_text(local_time: datetime) -> str:
    from lunar_python import Solar

    lunar = Solar.fromYmdHms(
        local_time.year,
        local_time.month,
        local_time.day,
        local_time.hour,
        local_time.minute,
        local_time.second,
    ).getLunar()
    return (
        f"{lunar.getYearInChinese()}年"
        f"{lunar.getMonthInChinese()}月"
        f"{lunar.getDayInChinese()}"
    )


def _display_width(value: str) -> int:
    return sum(2 if east_asian_width(char) in {"W", "F"} else 1 for char in value)


def _pad(value: Any, width: int) -> str:
    text = str(value or "")
    return text + " " * max(0, width - _display_width(text))


def _line_text(line: Mapping[str, Any] | None) -> str:
    if not line:
        return ""
    return (
        f"{line.get('relative') or ''}"
        f"{line.get('earthly_branch') or ''}"
        f"{line.get('element') or ''}"
    )


def _hidden_text(line: Mapping[str, Any]) -> str:
    hidden = line.get("hidden_spirit")
    if not isinstance(hidden, Mapping):
        return ""
    najia = str(hidden.get("najia") or "")
    branch = najia[-1:] if najia else str(hidden.get("earthly_branch") or "")
    return f"{hidden.get('relative') or ''}{branch}{hidden.get('element') or ''}"


def _line_symbol(line: Mapping[str, Any] | None) -> str:
    if not line:
        return ""
    return "---" if line.get("yin_yang") == "yang" else "- -"


def _movement_mark(line: Mapping[str, Any]) -> str:
    if not line.get("changing"):
        return ""
    return "〇" if line.get("yin_yang") == "yang" else "×"


def _primary_qualifier(chart: Mapping[str, Any], primary: Mapping[str, Any]) -> str:
    bits = str(primary.get("bits") or "")
    palace_type = str((_as_dict(chart.get("palace"))).get("type") or "")
    if palace_type == "本宫":
        return "六冲"
    if bits in LIUHE_BITS:
        return "六合"
    if palace_type in {"游魂", "归魂"}:
        return palace_type
    return ""


def _hexagram_heading(chart: Mapping[str, Any]) -> tuple[str, str]:
    primary = _as_dict(chart.get("primary"))
    palace = _as_dict(chart.get("palace"))
    qualifier = _primary_qualifier(chart, primary)
    primary_suffix = f",{qualifier}" if qualifier else ""
    primary_heading = f"{primary.get('name') or ''}({palace.get('gua') or ''}{primary_suffix})"

    changed = _as_dict(chart.get("changed")) if chart.get("changed") else {}
    if not changed:
        return primary_heading, ""
    changed_palace = PALACE_TABLE.get(str(changed.get("bits") or ""), ("", "", 0))[0]
    return primary_heading, f"{changed.get('name') or ''}({changed_palace})"


def _format_line_rows(chart: Mapping[str, Any]) -> tuple[str, str]:
    primary_lines = {
        int(line.get("position") or 0): line
        for line in chart.get("lines") or []
        if isinstance(line, Mapping)
    }
    changed_chart = _as_dict(chart.get("changed")) if chart.get("changed") else {}
    changed_lines = {
        int(line.get("position") or 0): line
        for line in changed_chart.get("lines") or []
        if isinstance(line, Mapping)
    }
    has_hidden = any(_hidden_text(line) for line in primary_lines.values())
    header = (
        "六神 伏神　　 本卦　　　　　　  　  　 　 变卦　　　 　  "
        if has_hidden
        else "六神 本卦　　　　　  　  　 　 变卦　　　 　  "
    )

    rows: list[str] = []
    for position in range(6, 0, -1):
        primary = primary_lines[position]
        changed = changed_lines.get(position)
        spirit = str(primary.get("spirit") or "").replace("螣蛇", "腾蛇")
        primary_part = (
            f"{_pad(_line_text(primary), 10)} "
            f"{_pad(_line_symbol(primary), 4)} "
            f"{_pad(_movement_mark(primary), 2)} "
            f"{_pad(primary.get('shi_ying'), 3)}"
        )
        changed_part = (
            f"{_pad(_line_text(changed), 10)} "
            f"{_pad(_line_symbol(changed), 4)} "
            f"{str(changed.get('shi_ying') or '') if changed else ''}"
        )
        if has_hidden:
            row = f"{spirit} {_pad(_hidden_text(primary), 9)} {primary_part} {changed_part}"
        else:
            row = f"{spirit} {primary_part} {changed_part}"
        rows.append(row.rstrip())
    return header.rstrip(), "\n".join(rows)


def chart_to_text(chart: Mapping[str, Any] | Any) -> str:
    """Render the chart as the compact text block used by analysis prompts."""
    data = _as_dict(chart)
    local_time = _local_cast_time(data)
    pillars = _as_dict(data.get("four_pillars"))
    year_pillar = str(pillars.get("year") or "").removesuffix("年") + "年"
    month_branch = str(data.get("month_branch") or str(pillars.get("month") or "")[-1:])
    day_pillar = str(data.get("day_pillar") or pillars.get("day") or "").removesuffix("日") + "日"
    hour_branch = str(pillars.get("hour") or "")[-1:]
    xunkong = "".join(str(item) for item in data.get("xunkong") or [])
    primary_heading, changed_heading = _hexagram_heading(data)
    table_header, line_rows = _format_line_rows(data)
    hexagram_heading = f"　　 　　　　 {primary_heading} 　  　 　 {changed_heading}".rstrip()

    return (
        "日期:\n"
        f"公历[{local_time.year}年{local_time.month}月{local_time.day}日  "
        f"{local_time.hour}时{local_time.minute:02d}分 {_WEEKDAYS[local_time.weekday()]}]\n"
        f"农历[{_lunar_date_text(local_time)}]\n"
        "四柱:\n"
        f"年柱[{year_pillar}]\t月柱[{month_branch}月]\t日柱[{day_pillar}]\t"
        f"时柱[{hour_branch}时]\t旬空[{xunkong}]\n"
        f"{hexagram_heading}\n"
        f"{table_header}\n"
        f"{line_rows}"
    )
