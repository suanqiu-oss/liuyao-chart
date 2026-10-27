from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from liuyao_chart import cast


def _chart() -> object:
    return cast(
        lines=[8, 8, 7, 6, 7, 7],
        at=datetime(2026, 7, 20, 12, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
    )


def test_text_contains_pillars_and_hexagram_headings():
    text = _chart().to_text()
    assert "公历[2026年7月20日" in text
    assert "四柱:" in text
    assert "旬空[" in text
    assert "风山渐(艮" in text
    assert "天山遁(乾)" in text
    assert "腾蛇" in text or "螣蛇" in text


def test_text_marks_six_clash_and_hidden_spirits():
    static = cast(
        lines=[7] * 6,
        at=datetime(2026, 7, 20, 12, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    assert "六冲" in static.to_text()

    # 天风姤缺妻财与父母，必现伏神
    with_hidden = cast(
        lines=[8, 7, 7, 7, 7, 7],
        at=datetime(2026, 7, 20, 12, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    assert "伏神" in with_hidden.to_text()


def test_text_requires_cast_time():
    from liuyao_chart.chart import LiuyaoChart

    bare = _chart().model_dump(mode="json")
    bare.pop("cast_time")
    bare.pop("timezone")
    import pytest

    with pytest.raises(ValueError):
        LiuyaoChart.model_validate(bare).to_text()


def test_text_without_timezone_uses_cast_time_offset_not_machine_zone(monkeypatch):
    from liuyao_chart.chart import LiuyaoChart

    payload = _chart().model_dump(mode="json")
    payload["timezone"] = None
    chart = LiuyaoChart.model_validate(payload)
    expected = chart.to_text()
    monkeypatch.setenv("TZ", "America/Los_Angeles")
    import time
    if hasattr(time, "tzset"):
        time.tzset()
    assert chart.to_text() == expected
    assert "公历[2026年7月20日" in expected
