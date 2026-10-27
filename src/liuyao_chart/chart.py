"""Deterministic Liuyao casting and chart assembly (``liuyao_chart.v1``).

``cast`` is the single entry point: give six raw line values (6/7/8/9, bottom
to top) and an aware cast datetime, get the assembled hexagram chart with
najia, six relatives, six spirits, shi/ying, hidden spirits and the changed
hexagram.

The ``align_changed_relatives`` validator intentionally re-derives changed
relatives on every validation: charts stored by earlier engine versions may
carry relatives computed against the changed hexagram's own palace, and this
keeps them consistent with the primary palace without a data migration.
"""
from __future__ import annotations

import secrets
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .calendar import _four_pillars
from .tables import (
    GUA64,
    NAJIA,
    PALACE_TABLE,
    PALACE_WUXING,
    SHENG,
    KE,
    SIX_SPIRITS,
    TRIGRAM_BITS,
    TRIGRAM_NAME,
    ZHI_WUXING,
)

ENGINE_VERSION = "0.1.0"


class LiuyaoLine(BaseModel):
    position: int
    value: int
    yin_yang: Literal["yin", "yang"]
    changing: bool
    changing_label: str | None = None
    najia: str
    heavenly_stem: str
    earthly_branch: str
    element: str
    relative: str
    spirit: str
    shi_ying: Literal["世", "应"] | None = None
    hidden_spirit: dict | None = None


class LiuyaoHexagram(BaseModel):
    bits: str
    name: str
    upper_trigram: str
    lower_trigram: str
    lines: list[LiuyaoLine]


class LiuyaoChart(BaseModel):
    schema_version: str = "liuyao_chart.v1"
    cast_time: datetime | None = None
    timezone: str | None = None
    four_pillars: dict[str, str]
    month_branch: str
    day_pillar: str
    xunkong: list[str]
    palace: dict[str, str | int]
    primary: LiuyaoHexagram
    changed: LiuyaoHexagram | None = None
    lines: list[LiuyaoLine]
    moving_lines: list[int]
    engine: dict[str, str]
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def align_changed_relatives(self) -> "LiuyaoChart":
        """New and stored casts both use the primary palace for changed relatives."""
        if self.changed is not None:
            palace = PALACE_TABLE[self.primary.bits][0]
            element = PALACE_WUXING[palace]
            for line in self.changed.lines:
                line.relative = _relative(line.element, element)
        return self

    def to_text(self) -> str:
        from .text import chart_to_text

        return chart_to_text(self)


class LiuyaoCastError(ValueError):
    """Raised when the raw line values are invalid."""


def auto_lines() -> list[int]:
    """Simulate three independent fair coins for each of six lines."""
    return [6 + sum(secrets.randbelow(2) for _ in range(3)) for _ in range(6)]


def _validate_lines(lines: list[int]) -> None:
    if len(lines) != 6 or any(line not in {6, 7, 8, 9} for line in lines):
        raise LiuyaoCastError("lines must contain exactly six values from 6, 7, 8, 9")


def _relative(line_element: str, palace_element: str) -> str:
    if line_element == palace_element:
        return "兄弟"
    if SHENG[line_element] == palace_element:
        return "父母"
    if SHENG[palace_element] == line_element:
        return "子孙"
    if KE[line_element] == palace_element:
        return "官鬼"
    return "妻财"


def _spirit_start(day_stem: str) -> int:
    return {"甲": 0, "乙": 0, "丙": 1, "丁": 1, "戊": 2, "己": 3,
            "庚": 4, "辛": 4, "壬": 5, "癸": 5}[day_stem]


def _assemble_hexagram(
    bits: str,
    day_stem: str,
    raw_values: list[int],
    moving: set[int],
    *,
    include_hidden: bool = True,
) -> tuple[LiuyaoHexagram, dict[str, str | int]]:
    palace, palace_type, shi = PALACE_TABLE[bits]
    ying = shi + 3 if shi <= 3 else shi - 3
    palace_element = PALACE_WUXING[palace]
    lower, upper = TRIGRAM_NAME[bits[:3]], TRIGRAM_NAME[bits[3:]]
    inner_stem, inner_branches, _, _ = NAJIA[lower]
    _, _, outer_stem, outer_branches = NAJIA[upper]
    stems = [inner_stem] * 3 + [outer_stem] * 3
    branches = list(inner_branches + outer_branches)
    start = _spirit_start(day_stem)
    lines: list[LiuyaoLine] = []
    for index, bit in enumerate(bits):
        position = index + 1
        branch = branches[index]
        value = raw_values[index]
        lines.append(LiuyaoLine(
            position=position,
            value=value,
            yin_yang="yang" if bit == "1" else "yin",
            changing=position in moving,
            changing_label=("老阳" if value == 9 else "老阴") if position in moving else None,
            najia=stems[index] + branch,
            heavenly_stem=stems[index],
            earthly_branch=branch,
            element=ZHI_WUXING[branch],
            relative=_relative(ZHI_WUXING[branch], palace_element),
            spirit=SIX_SPIRITS[(start + index) % 6],
            shi_ying="世" if position == shi else ("应" if position == ying else None),
        ))
    if include_hidden:
        present = {line.relative for line in lines}
        pure, _ = _assemble_hexagram(TRIGRAM_BITS[palace] * 2, day_stem, [7] * 6, set(), include_hidden=False)
        for pure_line in pure.lines:
            if pure_line.relative not in present:
                lines[pure_line.position - 1].hidden_spirit = {
                    "relative": pure_line.relative,
                    "najia": pure_line.najia,
                    "element": pure_line.element,
                }
    hexagram = LiuyaoHexagram(
        bits=bits,
        name=GUA64[bits],
        upper_trigram=upper,
        lower_trigram=lower,
        lines=lines,
    )
    return hexagram, {
        "gua": palace, "element": palace_element, "type": palace_type,
        "shi_position": shi, "ying_position": ying,
    }


def cast(
    lines: list[int],
    at: datetime,
    timezone: str | None = None,
) -> LiuyaoChart:
    """Assemble the chart for six raw line values (bottom to top, 6/7/8/9).

    ``at`` must be an aware datetime.  ``timezone`` overrides the IANA zone
    used to localise ``at``; by default the datetime's own ``tzinfo`` is used.
    """
    lines = list(lines)
    _validate_lines(lines)
    if at.tzinfo is None or at.utcoffset() is None:
        raise LiuyaoCastError("cast time must include a UTC offset")

    bits = "".join("1" if value in {7, 9} else "0" for value in lines)
    moving = {index + 1 for index, value in enumerate(lines) if value in {6, 9}}
    changed_bits = "".join(
        str(1 - int(bit)) if index + 1 in moving else bit
        for index, bit in enumerate(bits)
    )
    pillars, xunkong = _four_pillars(at, timezone)
    primary, palace = _assemble_hexagram(bits, pillars["day"][0], lines, moving)
    changed = None
    if moving:
        changed_values = [7 if bit == "1" else 8 for bit in changed_bits]
        changed, _ = _assemble_hexagram(
            changed_bits, pillars["day"][0], changed_values, set(), include_hidden=False
        )
    tz_name = timezone or getattr(at.tzinfo, "key", None)
    return LiuyaoChart(
        cast_time=at,
        timezone=tz_name,
        four_pillars=pillars,
        month_branch=pillars["month"][1],
        day_pillar=pillars["day"],
        xunkong=xunkong,
        palace=palace,
        primary=primary,
        changed=changed,
        lines=primary.lines,
        moving_lines=sorted(moving),
        engine={
            "name": "liuyao-chart",
            "version": ENGINE_VERSION,
            "calendar": "lunar-python",
            "reference": "yaomancy/liuyao-engine@0.1.0",
        },
        warnings=[],
    )
