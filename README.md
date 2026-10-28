# liuyao-chart

[![PyPI](https://img.shields.io/pypi/v/liuyao-chart)](https://pypi.org/project/liuyao-chart/)
[![Python](https://img.shields.io/pypi/pyversions/liuyao-chart)](https://pypi.org/project/liuyao-chart/)
[![CI](https://github.com/suanqiu-oss/liuyao-chart/actions/workflows/ci.yml/badge.svg)](https://github.com/suanqiu-oss/liuyao-chart/actions/workflows/ci.yml)
[![License](https://img.shields.io/pypi/l/liuyao-chart)](https://github.com/suanqiu-oss/liuyao-chart/blob/main/LICENSE)

确定性六爻排盘库：输入六次起卦爻值（初爻到上爻，6/7/8/9）和起卦时刻，输出装卦、
纳甲、六亲、六神、世应、伏神与变卦的带版本号 JSON（`liuyao_chart.v1`）。

纯 Python，无 FastAPI / 数据库 / LLM 依赖；日历后端为
[lunar-python](https://github.com/6tail/lunar-python)（Windows 下 `sxtwl`
目前编译不过，故不作为依赖）。排盘规则改编自
[yaomancy/liuyao-engine](https://github.com/yaomancy/liuyao-engine) 0.1.0
（Apache-2.0），见 `NOTICE`。

## 安装

```bash
pip install liuyao-chart
```

## 使用

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from liuyao_chart import auto_lines, cast

chart = cast(
    lines=[7, 8, 9, 7, 6, 8],          # 初爻到上爻；6=老阴 7=少阳 8=少阴 9=老阳
    at=datetime(2026, 10, 27, 14, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
)
chart.model_dump(mode="json")   # liuyao_chart.v1，可直接给前端渲染
chart.to_text()                 # 纯文本卦盘

cast(lines=auto_lines(), at=...)  # secrets 模拟三钱法自动起卦
```

`at` 必须是带时区的 datetime。默认按它自带的 IANA 时区（`ZoneInfo`）换算
四柱；如果用的是固定偏移（`datetime.timezone(timedelta(hours=8))`），需要
另外传 `timezone="Asia/Shanghai"`，否则会报错。

## 默认口径

- **日界**：子初换日（23:00 起日柱进次日），与参考引擎一致。
- **年柱界**：lunar-python 默认（立春换年柱）。
- **变卦六亲**：一律按本卦宫五行取，兼容历史存储数据（见
  `LiuyaoChart.align_changed_relatives`）。

## 输出契约

`schema_version` 固定为 `liuyao_chart.v1`，JSON Schema 随包发布于
`liuyao_chart/schema/liuyao_chart.v1.json`。字段有破坏性变更时升级到 v2。

## 许可证

Apache-2.0。改编规则的第三方声明见 `NOTICE`。
