"""陕西桃树物候期推算。

输入：当前日期 + 可选品种/海拔修正。
输出：当前所处物候期 + 上下两个相邻物候期。

物候期数据来自 data/knowledge/peach_phenology.json（关中中熟桃为基线）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..infra.safeio import read_json


@dataclass
class Stage:
    key: str
    name: str
    start: tuple[int, int]  # (month, day)
    end: tuple[int, int]
    summary: str


def _parse_md(s: str) -> tuple[int, int]:
    m, d = s.split("-")
    return int(m), int(d)


def load_stages(phenology_path: Path) -> list[Stage]:
    data = read_json(phenology_path) or {}
    stages_raw = data.get("stages") or []
    out: list[Stage] = []
    for s in stages_raw:
        out.append(
            Stage(
                key=s["key"],
                name=s["name"],
                start=_parse_md(s["month_day_start"]),
                end=_parse_md(s["month_day_end"]),
                summary=s.get("summary", ""),
            )
        )
    return out


def _day_of_year(month: int, day: int, year: int) -> int:
    return date(year, month, day).timetuple().tm_yday


def current_stage(stages: list[Stage], today: date) -> Stage | None:
    """支持跨年区间（如休眠期 12-01 → 02-15）。"""
    y = today.year
    today_doy = today.timetuple().tm_yday
    for s in stages:
        start_doy = _day_of_year(*s.start, y)
        end_doy = _day_of_year(*s.end, y)
        if start_doy <= end_doy:
            if start_doy <= today_doy <= end_doy:
                return s
        else:
            # 跨年区间：12-01 → 02-15
            if today_doy >= start_doy or today_doy <= end_doy:
                return s
    return None


def neighbors(stages: list[Stage], current: Stage) -> tuple[Stage | None, Stage | None]:
    if not current:
        return None, None
    idx = next((i for i, s in enumerate(stages) if s.key == current.key), -1)
    if idx < 0:
        return None, None
    prev = stages[idx - 1] if idx > 0 else stages[-1]
    nxt = stages[(idx + 1) % len(stages)]
    return prev, nxt
