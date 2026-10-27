"""liuyao-chart: deterministic Liuyao casting and chart assembly.

>>> from liuyao_chart import cast, auto_lines
>>> chart = cast(lines=[7, 8, 9, 7, 6, 8], at=datetime(2026, 10, 27, 14, 30, tzinfo=ZoneInfo("Asia/Shanghai")))
>>> chart.model_dump(mode="json")["schema_version"]
'liuyao_chart.v1'
"""
from .chart import (
    LiuyaoCastError,
    LiuyaoChart,
    LiuyaoHexagram,
    LiuyaoLine,
    auto_lines,
    cast,
)

__all__ = [
    "LiuyaoCastError",
    "LiuyaoChart",
    "LiuyaoHexagram",
    "LiuyaoLine",
    "auto_lines",
    "cast",
]
__version__ = "0.1.0"
