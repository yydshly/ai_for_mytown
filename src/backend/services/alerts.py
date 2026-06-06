"""灾害预警规则引擎（硬规则，不依赖 LLM）。

R-02：极端灾害漏报=绝收，判断必须用确定性阈值规则，不能交给大模型。
每条规则结合 [天气阈值] × [当前物候期] 触发，并挂上 disaster_playbooks 的应对措施。
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..infra.safeio import read_json
from .weather import WeatherView

log = logging.getLogger("services.alerts")

_SEVERITY_RANK = {"severe": 3, "warning": 2, "info": 1}


def _playbooks(knowledge_dir: Path) -> dict:
    data = read_json(knowledge_dir / "disaster_playbooks.json") or {}
    return data.get("playbooks") or {}


def evaluate_alerts(weather: WeatherView, stage_key: str, knowledge_dir: Path) -> list[dict]:
    """返回当前生效的预警列表，按严重度降序。"""
    pb = _playbooks(knowledge_dir)
    alerts: list[dict] = []

    def add(kind: str, severity: str, reason: str):
        book = pb.get(kind) or {}
        # 物候期不在影响范围内则降级为提示
        affected = book.get("affected_stages") or []
        if affected and stage_key not in affected:
            severity = "info"
        alerts.append({
            "kind": kind,
            "name": book.get("name", kind),
            "icon": book.get("icon", "⚠️"),
            "severity": severity,
            "reason": reason,
            "threat": book.get("threat", ""),
            "measures": {
                "before": book.get("before", []),
                "during": book.get("during", []),
                "after": book.get("after", []),
            },
        })

    # --- 霜冻：夜间最低 ≤2℃，萌芽/花/幼果期最危险 ---
    if weather.night_min_temp <= 2:
        sev = "severe" if stage_key in ("bud_swell", "flowering", "young_fruit") else "warning"
        add("frost", sev, f"夜间最低气温 {weather.night_min_temp:.0f}℃")

    # --- 冰雹：预报含冰雹关键词，任意期都严重 ---
    if "冰雹" in weather.hazards:
        add("hail", "severe", "天气预报含冰雹")

    # --- 大风：风力 ≥6 级，膨大/采收期防折枝落果 ---
    if weather.wind_level >= 6:
        add("wind", "warning", f"风力 {weather.wind_level} 级")

    # --- 高温日灼：最高 ≥35℃，膨大/采收期 ---
    if weather.max_temp >= 35:
        add("heat", "warning", f"最高气温 {weather.max_temp:.0f}℃")

    # --- 连阴雨：未来 3 天≥3 雨天，褐腐病/裂果风险 ---
    if weather.precip_days >= 3:
        add("rain", "warning", f"未来 3 天有 {weather.precip_days} 天降雨")

    alerts.sort(key=lambda a: _SEVERITY_RANK.get(a["severity"], 0), reverse=True)
    return alerts
