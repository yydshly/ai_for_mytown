"""天气数据客户端。

返回归一化的天气视图，供灾害规则引擎判断（见 alerts.py）。
- 未配置 key：mock 模式，可用 scenario 注入不同灾害场景做联调。
- 配置 qweather key：走和风天气 HTTP（实时+3 天预报）。

设计为对无 key / 网络错误优雅降级（R-07）：失败时返回 mock 的平稳天气。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

log = logging.getLogger("services.weather")


@dataclass
class WeatherView:
    """归一化天气，供规则引擎使用。"""
    source: str                      # mock | qweather
    location_name: str
    night_min_temp: float            # 未来夜间最低气温 ℃
    max_temp: float                  # 未来最高气温 ℃
    wind_level: int                  # 风力等级（蒲福风级）
    precip_days: int                 # 未来 3 天降雨天数
    hazards: list[str] = field(default_factory=list)  # 预报中的灾害关键词（如 冰雹）
    summary: str = ""                # 人类可读概述


# 预设 mock 场景：联调用，触发不同灾害规则
_SCENARIOS: dict[str, dict] = {
    "none":  {"night_min_temp": 16, "max_temp": 28, "wind_level": 3, "precip_days": 0, "hazards": [], "summary": "晴到多云，气温平稳。"},
    "frost": {"night_min_temp": -2, "max_temp": 10, "wind_level": 2, "precip_days": 0, "hazards": [], "summary": "夜间强降温，最低 -2℃，有霜冻风险。"},
    "hail":  {"night_min_temp": 14, "max_temp": 26, "wind_level": 5, "precip_days": 1, "hazards": ["冰雹"], "summary": "午后强对流，局地有冰雹。"},
    "wind":  {"night_min_temp": 15, "max_temp": 27, "wind_level": 7, "precip_days": 0, "hazards": ["大风"], "summary": "大风 7 级，注意防折枝。"},
    "heat":  {"night_min_temp": 22, "max_temp": 37, "wind_level": 2, "precip_days": 0, "hazards": [], "summary": "持续高温，最高 37℃。"},
    "rain":  {"night_min_temp": 18, "max_temp": 24, "wind_level": 3, "precip_days": 3, "hazards": [], "summary": "未来三天连阴雨。"},
}


class WeatherClient:
    def __init__(self, config: dict):
        wcfg = config.get("weather") or {}
        self.provider = wcfg.get("provider", "qweather")
        self.api_key = (wcfg.get("api_key") or "").strip()
        loc = wcfg.get("default_location") or {}
        self.lat = loc.get("lat", 34.27)
        self.lon = loc.get("lon", 108.93)
        self.location_name = loc.get("name", "陕西")

    def _key_ready(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("PASTE_")

    async def get(self, scenario: str | None = None) -> WeatherView:
        # 显式指定 scenario，或没有可用 key → mock
        if scenario or not self._key_ready():
            return self._mock(scenario or "none")
        try:
            return await self._qweather()
        except Exception as e:
            log.warning("qweather 拉取失败，回退 mock: %s", e)
            return self._mock("none")

    def _mock(self, scenario: str) -> WeatherView:
        s = _SCENARIOS.get(scenario, _SCENARIOS["none"])
        return WeatherView(
            source="mock",
            location_name=self.location_name,
            night_min_temp=s["night_min_temp"],
            max_temp=s["max_temp"],
            wind_level=s["wind_level"],
            precip_days=s["precip_days"],
            hazards=list(s["hazards"]),
            summary=s["summary"],
        )

    async def _qweather(self) -> WeatherView:
        """和风天气 3 天预报。免费档：devapi.qweather.com。"""
        url = "https://devapi.qweather.com/v7/weather/3d"
        params = {"location": f"{self.lon:.2f},{self.lat:.2f}", "key": self.api_key}
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        daily = data.get("daily") or []
        if not daily:
            return self._mock("none")
        mins = [float(d["tempMin"]) for d in daily if d.get("tempMin") is not None]
        maxs = [float(d["tempMax"]) for d in daily if d.get("tempMax") is not None]
        winds = [int(d.get("windScaleDay", "0").split("-")[-1] or 0) for d in daily]
        texts = " ".join(d.get("textDay", "") + d.get("textNight", "") for d in daily)
        precip_days = sum(1 for d in daily if "雨" in (d.get("textDay", "") + d.get("textNight", "")))
        hazards = [k for k in ("冰雹", "大风", "暴雨", "雷暴") if k in texts]
        return WeatherView(
            source="qweather",
            location_name=self.location_name,
            night_min_temp=min(mins) if mins else 99,
            max_temp=max(maxs) if maxs else -99,
            wind_level=max(winds) if winds else 0,
            precip_days=precip_days,
            hazards=hazards,
            summary=f"未来3天 {min(mins):.0f}~{max(maxs):.0f}℃" if mins and maxs else "",
        )
