from __future__ import annotations

import sys
from datetime import datetime
from itertools import product
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from liuyao_chart import (  # noqa: E402
    LiuyaoCastError,
    LiuyaoChart,
    auto_lines,
    cast,
)
import liuyao_chart.chart as engine  # noqa: E402


def chart_for(lines, *, cast_time="2026-07-20T12:30:00+08:00", timezone="Asia/Shanghai"):
    return cast(lines=lines, at=datetime.fromisoformat(cast_time), timezone=timezone)


def test_line_values_map_to_yin_yang_moving_and_changed_hexagram():
    chart = chart_for([6, 7, 8, 9, 7, 8])
    assert [(line.value, line.yin_yang, line.changing) for line in chart.lines] == [
        (6, "yin", True),
        (7, "yang", False),
        (8, "yin", False),
        (9, "yang", True),
        (7, "yang", False),
        (8, "yin", False),
    ]
    assert chart.moving_lines == [1, 4]
    assert chart.primary.bits == "010110"
    assert chart.changed.bits == "110010"


def test_jian_to_dun_changed_fire_is_parent_and_stored_cast_is_repaired():
    chart = chart_for([8, 8, 7, 6, 7, 7])
    assert chart.primary.name == "风山渐"
    assert chart.changed.name == "天山遁"
    changed = chart.changed.lines[3]
    assert (changed.najia, changed.element, changed.relative) == ("壬午", "火", "父母")
    stored = chart.model_dump(mode="json")
    stored["changed"]["lines"][3]["relative"] = "官鬼"
    reloaded = LiuyaoChart.model_validate(stored)
    assert reloaded.changed.lines[3].relative == "父母"


def test_all_4096_casts_use_primary_palace_for_changed_relatives(monkeypatch):
    monkeypatch.setattr(engine, "_four_pillars", lambda *_: (
        {"year": "丙午", "month": "丁酉", "day": "辛亥", "hour": "戊戌"}, ["寅", "卯"],
    ))
    # Independent five-element cycle, rather than using the implementation helper.
    cycle = ["木", "火", "土", "金", "水"]
    labels = ["兄弟", "子孙", "妻财", "官鬼", "父母"]
    for values in product((6, 7, 8, 9), repeat=6):
        chart = cast(lines=list(values), at=datetime.fromisoformat(
            "2026-07-20T12:30:00+08:00"))
        if chart.changed is None:
            continue
        palace_index = cycle.index(chart.palace["element"])
        for line in chart.changed.lines:
            expected = labels[(cycle.index(line.element) - palace_index) % 5]
            assert line.relative == expected, (values, line.position)


def test_qian_no_moving_and_kun_all_moving_are_deterministic():
    qian = chart_for([7] * 6)
    assert qian.primary.name == "乾为天"
    assert qian.changed is None
    assert qian.palace["gua"] == "乾"
    assert qian.palace["shi_position"] == 6

    kun = chart_for([6] * 6)
    assert kun.changed.name == "乾为天"
    assert kun.moving_lines == [1, 2, 3, 4, 5, 6]


def test_raw_order_is_bottom_to_top_and_payload_is_auditable():
    chart = chart_for([6, 7, 8, 9, 6, 7])
    assert [line.position for line in chart.lines] == [1, 2, 3, 4, 5, 6]
    assert chart.schema_version == "liuyao_chart.v1"
    assert chart.engine["name"] == "liuyao-chart"
    assert chart.engine["reference"] == "yaomancy/liuyao-engine@0.1.0"


def test_cast_requires_offset_and_valid_iana_timezone():
    with pytest.raises(LiuyaoCastError, match="UTC offset"):
        cast(lines=[7] * 6, at=datetime(2026, 7, 20, 12, 30))
    with pytest.raises(ValueError, match="Unknown IANA timezone"):
        chart_for([7] * 6, timezone="Mars/Olympus")


def test_cast_rejects_invalid_lines():
    with pytest.raises(LiuyaoCastError):
        cast(lines=[7] * 5, at=datetime.fromisoformat("2026-07-20T12:30:00+08:00"))
    with pytest.raises(LiuyaoCastError):
        cast(lines=[5, 7, 8, 9, 7, 8], at=datetime.fromisoformat(
            "2026-07-20T12:30:00+08:00"))


def test_timezone_defaults_to_datetime_tzinfo():
    chart = cast(lines=[7] * 6,
                 at=datetime.fromisoformat("2026-07-20T12:30:00+08:00").astimezone(
                     ZoneInfo("Asia/Shanghai")))
    assert chart.timezone == "Asia/Shanghai"
    assert chart.four_pillars == chart_for([7] * 6).four_pillars


def test_fixed_offset_without_iana_zone_is_rejected():
    with pytest.raises(ValueError, match="IANA|timezone|aware"):
        cast(lines=[7] * 6, at=datetime.fromisoformat("2026-07-20T12:30:00+08:00"))


def test_three_coin_distribution_is_not_four_state_uniform():
    from collections import Counter

    counts = Counter(value for _ in range(4000) for value in auto_lines())
    total = sum(counts.values())
    expected = {6: 1 / 8, 7: 3 / 8, 8: 3 / 8, 9: 1 / 8}
    for value, probability in expected.items():
        assert abs(counts[value] / total - probability) < 0.025
