"""灾害预警路由（多作物）。

GET /api/alerts?crop=&scenario=  → 拉天气 + 当前物候期 + 硬规则评估 → 生效预警列表。
scenario（mock 用）：none/frost/hail/wind/heat/rain，便于无 key 时联调各类预警。
"""
from datetime import date

from fastapi import APIRouter, Query

from ..services.alerts import evaluate_alerts
from ..services.phenology import current_stage, load_stages
from ..services.weather import WeatherClient


def register(app, ctx) -> None:
    r = APIRouter()
    weather = WeatherClient(ctx.config)

    @r.get("/api/alerts")
    async def alerts(
        crop: str | None = Query(None),
        scenario: str | None = Query(None),
        lat: float | None = Query(None),
        lon: float | None = Query(None),
    ):
        cid = ctx.crops.resolve(crop)
        bundle = ctx.crops.knowledge(cid)
        wv = await weather.get(scenario, lat=lat, lon=lon)

        stages = load_stages(bundle.phenology_path)
        cur = current_stage(stages, date.today())
        stage_key = cur.key if cur else ""
        stage_name = cur.name if cur else ""

        active = evaluate_alerts(wv, stage_key, bundle.playbooks_path)
        return {
            "crop": cid,
            "weather": {
                "source": wv.source,
                "location": wv.location_name,
                "summary": wv.summary,
                "night_min_temp": wv.night_min_temp,
                "max_temp": wv.max_temp,
                "wind_level": wv.wind_level,
                "precip_days": wv.precip_days,
            },
            "stage": {"key": stage_key, "name": stage_name},
            "alerts": active,
            "count": len(active),
        }

    app.include_router(r)
