"""Golden snapshot tests: the engine output must match the exported snapshots
field-for-field (engine.name and the v1-only cast_time/timezone fields are
excluded from the comparison against the pre-split suanqiu payloads)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from liuyao_chart import cast

GOLDEN = Path(__file__).resolve().parent / "fixtures" / "golden" / "golden_liuyao.json"


def load_cases():
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert data["schema"] == "golden_liuyao.v1"
    return data["cases"]


CASES = load_cases()


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_matches_golden_snapshot(case):
    chart = cast(lines=case["lines"], at=datetime.fromisoformat(case["cast_time"]),
                 timezone=case["timezone"])
    got = chart.model_dump(mode="json")
    got["engine"]["name"] = "suanqiu-liuyao-adapter"
    got["engine"]["version"] = "1.0.0"
    got.pop("cast_time")
    got.pop("timezone")
    assert got == case["expected"]
