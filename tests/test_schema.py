"""The chart payload must validate against the bundled v1 JSON Schema."""
from __future__ import annotations

import json
from datetime import datetime
from importlib import resources
from zoneinfo import ZoneInfo

import pytest

jsonschema = pytest.importorskip("jsonschema")

from liuyao_chart import cast  # noqa: E402

SCHEMA = json.loads(
    resources.files("liuyao_chart").joinpath("schema/liuyao_chart.v1.json").read_text("utf-8")
)


@pytest.mark.parametrize("lines", [[7] * 6, [6, 7, 8, 9, 7, 8], [9] * 6])
def test_payload_validates(lines):
    chart = cast(lines=lines, at=datetime(2026, 7, 20, 12, 30, tzinfo=ZoneInfo("Asia/Shanghai")))
    jsonschema.validate(chart.model_dump(mode="json"), SCHEMA)
